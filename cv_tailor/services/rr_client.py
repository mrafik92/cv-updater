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
    """Async HTTP client for the Reactive-Resume v5 oRPC API.

    All procedures use POST with body ``{"json": <payload>}`` and
    responses are unwrapped from the same ``{"json": <data>}`` envelope.

    Auth: x-api-key header (Better Auth API key plugin). api_token is never logged.
    """

    def __init__(self, base_url: str, api_token: str, timeout: int = 30) -> None:
        self._api_base = base_url.rstrip("/") + "/api/rpc/resume"
        self._timeout = timeout
        self._headers = {
            "x-api-key": api_token,
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    async def list_resumes(self) -> list[dict[str, Any]]:
        raw = await self._rpc("list", {})
        if not isinstance(raw, list):
            raise RRClientError(f"Unexpected list_resumes response shape: {type(raw)}")
        return [_normalise_resume_meta(item) for item in raw]

    async def get_resume(self, resume_id: str) -> dict[str, Any]:
        raw = await self._rpc("getById", {"id": resume_id})
        if not isinstance(raw, dict):
            raise RRClientError(f"Unexpected get_resume response shape: {type(raw)}")
        resume = raw.get("data", raw)
        summary = resume.get("summary", {})
        if summary.get("content"):
            resume.setdefault("basics", {})["summary"] = summary["content"]
        return resume

    @staticmethod
    def _prepare_data(data: dict[str, Any]) -> dict[str, Any]:
        prepared = dict(data)
        summary_text = prepared.get("basics", {}).pop("summary", None)
        if summary_text and "summary" not in prepared:
            prepared["summary"] = {"title": "Summary", "columns": 1, "hidden": False, "content": summary_text}
        return prepared

    async def update_resume(self, resume_id: str, data: dict[str, Any]) -> dict[str, Any]:
        raw = await self._rpc("getById", {"id": resume_id})
        if not isinstance(raw, dict):
            raise RRClientError(f"Unexpected get_resume response shape: {type(raw)}")
        prepared = self._prepare_data(data)
        existing_data = raw.get("data", {})
        existing_data["basics"] = prepared.get("basics", existing_data.get("basics", {}))
        existing_data["sections"] = prepared.get("sections", existing_data.get("sections", {}))
        existing_data["summary"] = prepared.get("summary", existing_data.get("summary", {}))
        existing_data["metadata"] = prepared.get("metadata", existing_data.get("metadata", {}))
        result = await self._rpc("update", raw)
        if not isinstance(result, dict):
            raise RRClientError(f"Unexpected update_resume response shape: {type(result)}")
        return result

    async def create_resume(self, name: str, slug: str, data: dict[str, Any]) -> str:
        slug = slug or name.lower().replace(" ", "-")
        result = await self._rpc("create", {
            "name": name,
            "slug": slug,
            "tags": [],
            "withSampleData": False,
        })
        if not isinstance(result, str):
            raise RRClientError(f"Unexpected create_resume response: expected string id, got {type(result)}")
        new_id = result
        prepared = self._prepare_data(data)
        raw = await self._rpc("getById", {"id": new_id})
        if not isinstance(raw, dict):
            raise RRClientError(f"Unexpected get_resume after create: {type(raw)}")
        existing_data = raw.get("data", {})
        existing_data["basics"] = prepared.get("basics", existing_data.get("basics", {}))
        existing_data["sections"] = prepared.get("sections", existing_data.get("sections", {}))
        existing_data["summary"] = prepared.get("summary", existing_data.get("summary", {}))
        existing_data["metadata"] = prepared.get("metadata", existing_data.get("metadata", {}))
        await self._rpc("update", raw)
        return new_id

    async def _rpc(self, procedure: str, payload: dict[str, Any]) -> Any:
        url = f"{self._api_base}/{procedure}"
        body = {"json": payload} if payload else {"json": {}}
        resp = await self._request_with_retry("POST", url, body)
        data = resp.json()
        return data.get("json")

    async def _request_with_retry(
        self, method: str, url: str, body: dict[str, Any]
    ) -> httpx.Response:
        log = logger.bind(method=method, url=url)
        start = time.monotonic()
        attempt = 0
        while True:
            attempt += 1
            try:
                async with httpx.AsyncClient(timeout=self._timeout) as client:
                    resp = await client.request(
                        method, url, headers=self._headers, json=body
                    )
            except (httpx.TimeoutException, httpx.NetworkError) as exc:
                duration_ms = int((time.monotonic() - start) * 1000)
                log.warning("rr_client.timeout", duration_ms=duration_ms, attempt=attempt)
                if attempt >= 2:
                    raise RRUnavailableError(f"Timeout: {url}") from exc
                await asyncio.sleep(_RETRY_SLEEP)
                continue

            duration_ms = int((time.monotonic() - start) * 1000)
            log.info(
                "rr_client.response",
                status_code=resp.status_code,
                duration_ms=duration_ms,
                attempt=attempt,
            )

            if resp.status_code in (401, 403):
                raise RRAuthError(f"Auth failed HTTP {resp.status_code}: {url}")
            if resp.status_code == 404:
                raise RRNotFoundError(f"Not found: {url}")
            if resp.status_code in _RETRY_STATUSES:
                if attempt >= 2:
                    raise RRUnavailableError(
                        f"Service unavailable HTTP {resp.status_code}: {url}"
                    )
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
        **{
            k: v
            for k, v in item.items()
            if k not in {"id", "name", "title", "updatedAt", "updated_at"}
        },
    }