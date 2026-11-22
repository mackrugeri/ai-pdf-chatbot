"""One sanitized error envelope across route, validation and framework errors."""

import logging
from typing import NoReturn
from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException

from app.schemas.common import ErrorDetail, ErrorResponse

logger = logging.getLogger(__name__)


class APIError(Exception):
    def __init__(
        self,
        status_code: int,
        code: str,
        message: str,
        *,
        retryable: bool = False,
        headers: dict[str, str] | None = None,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.code = code
        self.message = message
        self.retryable = retryable
        self.headers = headers


def error_response(request: Request, error: APIError) -> JSONResponse:
    request_id = getattr(request.state, "request_id", uuid4())
    payload = ErrorResponse(
        error=ErrorDetail(
            code=error.code, message=error.message, retryable=error.retryable
        ),
        request_id=request_id,
    )
    return JSONResponse(
        status_code=error.status_code,
        content=payload.model_dump(mode="json"),
        headers={**(error.headers or {}), "X-Request-ID": str(request_id)},
    )


def not_implemented(feature: str) -> NoReturn:
    raise APIError(501, "NOT_IMPLEMENTED", f"{feature} is not implemented yet.")


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(APIError)
    async def handle_api_error(request: Request, exc: APIError) -> JSONResponse:
        return error_response(request, exc)

    @app.exception_handler(RequestValidationError)
    async def handle_validation_error(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        # Pydantic error details can include private request contents: never echo them.
        return error_response(
            request, APIError(422, "VALIDATION_ERROR", "Request validation failed.")
        )

    @app.exception_handler(HTTPException)
    async def handle_http_error(request: Request, exc: HTTPException) -> JSONResponse:
        messages = {404: "Resource not found.", 405: "Method not allowed."}
        return error_response(
            request,
            APIError(
                exc.status_code,
                f"HTTP_{exc.status_code}",
                messages.get(exc.status_code, "Request could not be processed."),
                headers=exc.headers,
            ),
        )
