from uuid import UUID

from fastapi.testclient import TestClient

from app.auth.verifier import AccessTokenIdentity
from app.config import Settings
from app.main import create_app
from app.storage.postgres.users import UserIdentity


class FakeVerifier:
    async def verify_access_token(self, token):
        assert token == "signed-access-token"
        return AccessTokenIdentity(
            issuer="http://localhost:8080/realms/ai-pdf-chatbot",
            subject="demo-subject",
            scopes=frozenset({"pdf:read", "pdf:write"}),
        )


def test_verified_identity_is_mapped_to_internal_user(monkeypatch):
    expected_id = UUID("0dcd940d-6a31-4861-bd64-e2335af74b50")
    resolved = []

    class FakeRepository:
        def __init__(self, pool):
            assert pool is not None

        async def resolve(self, issuer, subject):
            resolved.append((issuer, subject))
            return UserIdentity(expected_id, True)

    monkeypatch.setattr("app.api.dependencies.UserRepository", FakeRepository)
    api = create_app(Settings(app_env="test", _env_file=None))
    with TestClient(api) as client:
        api.state.oidc_verifier = FakeVerifier()
        api.state.database_pool = object()
        response = client.get(
            "/api/v1/capabilities",
            headers={"Authorization": "Bearer signed-access-token"},
        )

    assert response.status_code == 501
    assert resolved == [("http://localhost:8080/realms/ai-pdf-chatbot", "demo-subject")]


def test_inactive_identity_is_rejected(monkeypatch):
    class FakeRepository:
        def __init__(self, pool):
            pass

        async def resolve(self, issuer, subject):
            return UserIdentity(UUID(int=1), False)

    monkeypatch.setattr("app.api.dependencies.UserRepository", FakeRepository)
    api = create_app(Settings(app_env="test", _env_file=None))
    with TestClient(api) as client:
        api.state.oidc_verifier = FakeVerifier()
        api.state.database_pool = object()
        response = client.get(
            "/api/v1/capabilities",
            headers={"Authorization": "Bearer signed-access-token"},
        )
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "USER_INACTIVE"
