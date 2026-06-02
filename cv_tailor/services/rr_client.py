from __future__ import annotations

import asyncio
import time
from typing import Any

import httpx
import structlog

from cv_tailor.config import get_settings

logger = structlog.get_logger(__name__)


class RRClientError(Exception):
    """Base exception for all RR API client errors."""


class RRAuthError(RRClientError):
    """Raised on HTTP 401 or 403."""


class RRNotFoundError(RRClientError):
    """Raised on HTTP 404."""


class RRUnavailableError(RRClientError):
    """Raised on HTTP 5xx or network timeout."""


_RETRY_STATUSES = frozenset({500, 502, 503, 504})
_RETRY_SLEEP = 0.5


class RRClient:
    """Async HTTP client for the Reactive-Resume v5 API.

    Endpoints:
        GET /api/rpc/resumes          → resume.list  (metadata, no data field)
        GET /api/rpc/resumes/{id}     → resume.getById (full resume + data)
        GET /api/rpc/resumes/{id}/pdf → resume.export.downloadPdf (stream)

    Auth: x-api-key header (Better Auth API key plugin). api_token is never logged.
    """

    def __init__(self, base_url: str, api_token: str, timeout: int = 30) -> None:
        self._api_base = base_url.rstrip("/") + "/api/rpc"
        self._timeout = timeout
        self._headers = {"x-api-key": api_token, "Accept": "application/json"}

    async def list_resumes(self) -> list[dict[str, Any]]:
        raw: Any = await self._get("/resumes")
        if not isinstance(raw, list):
            raise RRClientError(f"Unexpected list_resumes response shape: {type(raw)}")
        return [_normalise_resume_meta(item) for item in raw]

    async def get_resume(self, resume_id: str) -> dict[str, Any]:
        raw: Any = await self._get(f"/resumes/{resume_id}")
        if not isinstance(raw, dict):
            raise RRClientError(f"Unexpected get_resume response shape: {type(raw)}")
        return raw  # type: ignore[return-value]

    async def print_resume(self, resume_id: str) -> bytes:
        url = f"{self._api_base}/resumes/{resume_id}/pdf"
        pdf_headers = {**self._headers, "Accept": "application/pdf"}
        resp = await self._request_with_retry("GET", url, pdf_headers)
        return resp.content

    async def _get(self, path: str) -> Any:
        url = f"{self._api_base}{path}"
        resp = await self._request_with_retry("GET", url, self._headers)
        return resp.json()

    async def _request_with_retry(
        self, method: str, url: str, headers: dict[str, str]
    ) -> httpx.Response:
        log = logger.bind(method=method, url=url)
        start = time.monotonic()
        attempt = 0
        while True:
            attempt += 1
            try:
                async with httpx.AsyncClient(timeout=self._timeout) as client:
                    resp = await client.request(method, url, headers=headers)
            except (httpx.TimeoutException, httpx.NetworkError) as exc:
                duration_ms = int((time.monotonic() - start) * 1000)
                log.warning("rr_client.timeout", duration_ms=duration_ms, attempt=attempt)
                if attempt >= 2:
                    raise RRUnavailableError(f"Timeout: {url}") from exc
                await asyncio.sleep(_RETRY_SLEEP)
                continue

            duration_ms = int((time.monotonic() - start) * 1000)
            log.info("rr_client.response", status_code=resp.status_code, duration_ms=duration_ms, attempt=attempt)

            if resp.status_code in (401, 403):
                raise RRAuthError(f"Auth failed HTTP {resp.status_code}: {url}")
            if resp.status_code == 404:
                raise RRNotFoundError(f"Not found: {url}")
            if resp.status_code in _RETRY_STATUSES:
                if attempt >= 2:
                    raise RRUnavailableError(f"Service unavailable HTTP {resp.status_code}: {url}")
                await asyncio.sleep(_RETRY_SLEEP)
                continue
            if resp.status_code >= 400:
                raise RRClientError(f"Unexpected HTTP {resp.status_code}: {url}")

            return resp


def get_rr_client() -> RRClient:
    settings = get_settings()
    return RRClient(
        base_url=settings.rr_base_url,
        api_token=settings.rr_api_token.get_secret_value(),
        timeout=settings.pdf_timeout_seconds,
    )


def _normalise_resume_meta(item: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": item.get("id"),
        "title": item.get("name") or item.get("title"),
        "updated_at": item.get("updatedAt") or item.get("updated_at"),
        **{k: v for k, v in item.items() if k not in {"id", "name", "title", "updatedAt", "updated_at"}},
    }
