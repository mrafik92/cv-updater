"""ASGI middleware for request correlation and structured request logging."""

from __future__ import annotations

import time
from uuid import uuid4

import structlog
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from structlog.contextvars import bind_contextvars, clear_contextvars


log = structlog.get_logger(__name__)


class RequestIDMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        clear_contextvars()
        request_id = str(uuid4())
        bind_contextvars(request_id=request_id)

        # Do not log resume content or feedback text verbatim; log IDs and lengths only.
        log.info("request_started", method=request.method, path=request.url.path)
        started_at = time.monotonic()

        try:
            response = await call_next(request)
        except Exception as exc:
            duration_ms = round((time.monotonic() - started_at) * 1000)
            log.error(
                "request_failed",
                method=request.method,
                path=request.url.path,
                duration_ms=duration_ms,
                error_type=type(exc).__name__,
            )
            raise

        response.headers["X-Request-ID"] = request_id

        duration_ms = round((time.monotonic() - started_at) * 1000)
        log.info(
            "request_finished",
            method=request.method,
            path=request.url.path,
            status_code=response.status_code,
            duration_ms=duration_ms,
        )
        return response
