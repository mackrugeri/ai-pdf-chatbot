"""Small authenticated FastAPI client used only by the Streamlit UI."""

from __future__ import annotations

import secrets
from typing import Any, Self

import httpx


class APIClientError(Exception):
    def __init__(
        self,
        message: str,
        *,
        status_code: int = 0,
        code: str = "API_ERROR",
        retryable: bool = False,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.code = code
        self.retryable = retryable


class AuthenticationExpired(APIClientError):
    pass


class APIClient:
    """Per-session API client. Never cache credentials across Streamlit users."""

    def __init__(self, base_url: str, access_token: str, *, timeout: float = 20.0):
        parsed = httpx.URL(base_url)
        if (
            parsed.scheme not in {"http", "https"}
            or not parsed.host
            or parsed.username
            or parsed.password
            or parsed.query
            or parsed.fragment
        ):
            raise ValueError("API base URL must be an absolute HTTP(S) origin")
        if not access_token or len(access_token) > 16_384:
            raise ValueError("A bounded access token is required")
        self._base_url = str(parsed).rstrip("/")
        self._access_token = access_token
        self._timeout = httpx.Timeout(timeout)
        self._client = httpx.Client(
            timeout=self._timeout,
            trust_env=False,
            follow_redirects=False,
            headers={"Authorization": f"Bearer {access_token}"},
        )

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> Self:
        return self

    def __exit__(self, *_: object) -> None:
        self.close()

    def get(self, path: str, *, params: dict[str, Any] | None = None) -> Any:
        return self._request("GET", path, params=params)

    def post(
        self,
        path: str,
        *,
        json_body: dict[str, Any] | None = None,
        idempotency_key: str | None = None,
    ) -> Any:
        return self._request(
            "POST", path, json_body=json_body, idempotency_key=idempotency_key
        )

    def delete(self, path: str, *, idempotency_key: str | None = None) -> Any:
        return self._request("DELETE", path, idempotency_key=idempotency_key)

    def upload_pdf(self, filename: str, content: bytes) -> dict[str, Any]:
        created = self.post(
            "/uploads",
            json_body={"filename": filename, "size_bytes": len(content)},
            idempotency_key=secrets.token_urlsafe(24),
        )
        if not isinstance(created, dict):
            raise APIClientError("The upload API returned an invalid response.")
        upload_id = created.get("upload_id")
        upload_url = created.get("upload_url")
        if not isinstance(upload_id, str) or not isinstance(upload_url, str):
            raise APIClientError("The upload API returned an invalid target.")

        target = httpx.URL(upload_url)
        if (
            target.scheme not in {"http", "https"}
            or not target.host
            or target.username
            or target.password
        ):
            raise APIClientError("The upload target is invalid.")
        # Use a separate client so the API Bearer token never reaches object storage.
        try:
            with httpx.Client(
                timeout=self._timeout, trust_env=False, follow_redirects=False
            ) as upload_client:
                response = upload_client.put(
                    upload_url,
                    content=content,
                    headers={"Content-Type": "application/pdf"},
                )
        except httpx.HTTPError:
            raise APIClientError(
                "The PDF could not be transferred to its temporary upload target.",
                code="UPLOAD_TRANSFER_FAILED",
                retryable=True,
            ) from None
        if not response.is_success:
            raise APIClientError(
                "The temporary upload target rejected the PDF.",
                status_code=response.status_code,
                code="UPLOAD_TRANSFER_REJECTED",
                retryable=response.status_code >= 500,
            )

        return self.post(
            f"/uploads/{upload_id}/complete",
            idempotency_key=secrets.token_urlsafe(24),
        )

    def _request(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        json_body: dict[str, Any] | None = None,
        idempotency_key: str | None = None,
    ) -> Any:
        if not path.startswith("/") or path.startswith("//"):
            raise ValueError("API path must be relative to the configured API origin")
        headers = {}
        if idempotency_key is not None:
            headers["Idempotency-Key"] = idempotency_key
        try:
            response = self._client.request(
                method,
                f"{self._base_url}/api/v1{path}",
                params=params,
                json=json_body,
                headers=headers,
            )
        except httpx.TimeoutException:
            raise APIClientError(
                "The API request timed out.", code="API_TIMEOUT", retryable=True
            ) from None
        except httpx.HTTPError:
            raise APIClientError(
                "The API is unavailable.", code="API_UNAVAILABLE", retryable=True
            ) from None

        if response.status_code == 401:
            raise AuthenticationExpired(
                "Your sign-in has expired. Please sign in again.",
                status_code=401,
                code="AUTHENTICATION_EXPIRED",
            )
        try:
            payload = response.json() if response.content else None
        except ValueError:
            payload = None
        if not response.is_success:
            error = payload.get("error", {}) if isinstance(payload, dict) else {}
            if not isinstance(error, dict):
                error = {}
            raise APIClientError(
                error.get("message", "The API could not complete this operation."),
                status_code=response.status_code,
                code=error.get("code", f"HTTP_{response.status_code}"),
                retryable=bool(error.get("retryable", response.status_code >= 500)),
            )
        return payload
