"""FastAPI application factory. No database/model connections are opened on import."""

import logging
from uuid import uuid4

from fastapi import FastAPI, Request
from starlette.middleware.base import RequestResponseEndpoint
from starlette.responses import Response

from app.api.errors import APIError, error_response, register_error_handlers
from app.api.health import router as health_router
from app.api.v1.router import router as api_router
from app.config import Settings
from app.schemas.common import ErrorResponse

logger = logging.getLogger(__name__)


def create_app(settings: Settings | None = None) -> FastAPI:
    config = settings if settings is not None else Settings()
    development_docs = config.app_env != "production"
    application = FastAPI(
        title=config.app_name,
        version="0.1.0",
        description="API scaffold: document and model services are not implemented yet.",
        docs_url="/docs" if development_docs else None,
        redoc_url="/redoc" if development_docs else None,
        openapi_url="/openapi.json" if development_docs else None,
        debug=False,
        responses={503: {"model": ErrorResponse}},
    )
    application.state.settings = config
    register_error_handlers(application)

    @application.middleware("http")
    async def request_context(
        request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        # Generate server-side IDs rather than reflecting arbitrary client headers.
        request.state.request_id = uuid4()
        try:
            response = await call_next(request)
        except Exception:
            # Exception strings/tracebacks can contain credentials or document text.
            logger.error("Unhandled API error; request_id=%s", request.state.request_id)
            response = error_response(
                request, APIError(500, "INTERNAL_ERROR", "An internal error occurred.")
            )
        response.headers["X-Request-ID"] = str(request.state.request_id)
        return response

    application.include_router(health_router)
    application.include_router(api_router)
    return application


app = create_app()
