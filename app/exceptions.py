"""Centralised exception handlers                    translates domain errors to HTTP responses."""

from __future__ import annotations

import logging

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)


class NotFoundError(Exception):
    """Raised when a requested resource does not exist."""
    def __init__(self, detail: str) -> None:
        self.detail = detail
        super().__init__(detail)


class ServiceError(Exception):
    """Raised when a downstream service (broker, data feed) fails."""
    def __init__(self, detail: str) -> None:
        self.detail = detail
        super().__init__(detail)


def register_exception_handlers(app: FastAPI) -> None:
    """Attach all exception handlers to the FastAPI application."""

    @app.exception_handler(NotFoundError)
    async def not_found_handler(request: Request, exc: NotFoundError) -> JSONResponse:
        return JSONResponse(status_code=404, content={"detail": exc.detail})

    @app.exception_handler(ServiceError)
    async def service_error_handler(request: Request, exc: ServiceError) -> JSONResponse:
        logger.error("ServiceError on %s: %s", request.url, exc.detail)
        return JSONResponse(status_code=502, content={"detail": exc.detail})

    @app.exception_handler(Exception)
    async def unhandled_handler(request: Request, exc: Exception) -> JSONResponse:
        logger.exception("Unhandled error on %s", request.url)
        return JSONResponse(
            status_code=500,
            content={"detail": "An internal error occurred. Check server logs."},
        )