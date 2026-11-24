from uuid import UUID

import pytest
from fastapi.testclient import TestClient

from app.api.dependencies import Principal, require_principal
from app.config import Settings
from app.main import create_app

DOCUMENT_ID = "0dcd940d-6a31-4861-bd64-e2335af74b50"
ROUTES = [
    ("GET", "/api/v1/capabilities", None),
    ("POST", "/api/v1/uploads", {"filename": "sample.pdf", "size_bytes": 100}),
    ("POST", f"/api/v1/uploads/{DOCUMENT_ID}/complete", None),
    ("GET", "/api/v1/documents", None),
    ("GET", f"/api/v1/documents/{DOCUMENT_ID}", None),
    ("GET", f"/api/v1/documents/{DOCUMENT_ID}/download", None),
    ("POST", f"/api/v1/documents/{DOCUMENT_ID}/retry", None),
    ("DELETE", f"/api/v1/documents/{DOCUMENT_ID}", None),
    (
        "POST",
        "/api/v1/chat",
        {"question": "What is covered?", "document_ids": [DOCUMENT_ID]},
    ),
    ("GET", "/api/v1/jobs", None),
    ("GET", f"/api/v1/jobs/{DOCUMENT_ID}", None),
    ("POST", f"/api/v1/jobs/{DOCUMENT_ID}/cancel", None),
]


@pytest.fixture
def api():
    return create_app(Settings(app_env="test", _env_file=None))


@pytest.fixture
def client(api):
    with TestClient(api) as test_client:
        yield test_client


@pytest.fixture
def authorized_client(api):
    # Test-only override. Production code never accepts this synthetic principal.
    api.dependency_overrides[require_principal] = lambda: Principal(UUID(DOCUMENT_ID))
    with TestClient(api) as test_client:
        yield test_client
    api.dependency_overrides.clear()


def test_liveness_does_not_claim_dependency_readiness(client):
    live = client.get("/health/live")
    assert live.status_code == 200
    assert live.json() == {"status": "alive"}
    UUID(live.headers["X-Request-ID"])
    ready = client.get("/health/ready")
    assert ready.status_code == 503
    assert ready.json()["error"]["code"] == "NOT_READY"
    assert ready.json()["request_id"] == ready.headers["X-Request-ID"]


@pytest.mark.parametrize("method,path,body", ROUTES)
def test_every_data_route_requires_authentication(client, method, path, body):
    response = client.request(
        method, path, json=body, headers={"Idempotency-Key": "test-key"}
    )
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "AUTHENTICATION_REQUIRED"
    assert response.headers["WWW-Authenticate"] == "Bearer"


@pytest.mark.parametrize("method,path,body", ROUTES)
def test_arbitrary_bearer_tokens_are_never_accepted(client, method, path, body):
    response = client.request(
        method,
        path,
        json=body,
        headers={
            "Authorization": "Bearer not-a-verified-token",
            "Idempotency-Key": "test-key",
        },
    )
    assert response.status_code == 503
    assert response.json()["error"]["code"] == "AUTH_NOT_CONFIGURED"


@pytest.mark.parametrize("method,path,body", ROUTES)
def test_route_shells_never_pretend_to_perform_business_operations(
    authorized_client, method, path, body
):
    response = authorized_client.request(
        method, path, json=body, headers={"Idempotency-Key": "test-key"}
    )
    assert response.status_code == 501
    assert response.json()["error"]["code"] == "NOT_IMPLEMENTED"


@pytest.mark.parametrize(
    "body",
    [
        {"question": "   ", "document_ids": [DOCUMENT_ID]},
        {"question": "x" * 2001, "document_ids": [DOCUMENT_ID]},
        {"question": "Private question", "document_ids": []},
        {"question": "Private question", "document_ids": [DOCUMENT_ID, DOCUMENT_ID]},
        {
            "question": "Private question",
            "document_ids": [DOCUMENT_ID],
            "owner_id": DOCUMENT_ID,
        },
    ],
)
def test_invalid_chat_input_is_rejected_without_echoing_private_content(
    authorized_client, body
):
    response = authorized_client.post(
        "/api/v1/chat", json=body, headers={"Idempotency-Key": "test-key"}
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"
    assert "Private question" not in response.text
    assert DOCUMENT_ID not in response.text


@pytest.mark.parametrize("size", [0, -1, 20 * 1024 * 1024 + 1])
def test_upload_metadata_limits(authorized_client, size):
    response = authorized_client.post(
        "/api/v1/uploads",
        json={"filename": "sample.pdf", "size_bytes": size},
        headers={"Idempotency-Key": "test-key"},
    )
    assert response.status_code == 422


@pytest.mark.parametrize("key", [None, "   ", "x" * 129])
def test_mutations_require_a_bounded_nonempty_idempotency_key(authorized_client, key):
    headers = {} if key is None else {"Idempotency-Key": key}
    response = authorized_client.post(
        "/api/v1/chat",
        json={"question": "Hello", "document_ids": [DOCUMENT_ID]},
        headers=headers,
    )
    assert response.status_code == 422


@pytest.mark.parametrize(
    "path",
    [
        "/api/v1/documents?limit=101",
        "/api/v1/jobs?limit=0",
        "/api/v1/jobs?state=unknown",
        "/api/v1/jobs?type=unknown",
        "/api/v1/documents/not-a-uuid",
    ],
)
def test_pagination_filters_and_resource_ids_are_validated(authorized_client, path):
    assert authorized_client.get(path).status_code == 422


def test_framework_errors_share_the_envelope_and_request_id(client):
    response = client.get(
        "/missing", headers={"X-Request-ID": "untrusted-client-value"}
    )
    assert response.status_code == 404
    assert set(response.json()) == {"error", "request_id"}
    assert response.json()["request_id"] == response.headers["X-Request-ID"]
    assert response.headers["X-Request-ID"] != "untrusted-client-value"


def test_unexpected_exceptions_do_not_expose_private_details(api, caplog):
    @api.get("/test-error")
    async def failure():
        raise RuntimeError("private-document-text-and-password")

    with TestClient(api, raise_server_exceptions=False) as test_client:
        response = test_client.get("/test-error")
    assert response.status_code == 500
    assert response.json()["error"]["code"] == "INTERNAL_ERROR"
    assert "private-document-text-and-password" not in response.text + caplog.text
    assert response.json()["request_id"] == response.headers["X-Request-ID"]


def test_openapi_exposes_bearer_auth_and_typed_contracts(client):
    schema = client.get("/openapi.json").json()
    for path, operations in schema["paths"].items():
        if path.startswith("/api/v1/"):
            for operation in operations.values():
                assert operation["security"] == [{"HTTPBearer": []}]
    assert "ChatRequest" in schema["components"]["schemas"]
    assert "JobResponse" in schema["components"]["schemas"]
    assert "DocumentResponse" in schema["components"]["schemas"]


def test_interactive_docs_are_disabled_in_production():
    api = create_app(
        Settings(app_env="test", _env_file=None).model_copy(
            update={"app_env": "production"}
        )
    )
    with TestClient(api) as test_client:
        for path in ["/docs", "/redoc", "/openapi.json"]:
            assert test_client.get(path).status_code == 404
        assert test_client.get("/api/v1/jobs").status_code == 401
