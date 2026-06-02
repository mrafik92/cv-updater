from __future__ import annotations

import json
import time
from typing import Any

import httpx
import structlog

log = structlog.get_logger(__name__)


class OpenRouterError(Exception):
    def __init__(self, status_code: int, body: str):
        super().__init__(f"OpenRouter error {status_code}: {body[:500]}")
        self.status_code = status_code
        self.body = body


class OpenRouterClient:
    def __init__(self, api_key: str, base_url: str, model: str, timeout: int = 120):
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout = timeout

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "HTTP-Referer": "https://github.com/user/cv-tailor",
            "X-Title": "CV Tailor",
            "Content-Type": "application/json",
        }

    async def generate_json(
        self,
        system: str,
        user: str,
        schema: dict[str, Any],
        max_retries: int = 2,
    ) -> dict[str, Any]:
        messages = [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ]
        payload = {
            "model": self.model,
            "messages": messages,
            "response_format": {
                "type": "json_schema",
                "json_schema": {"name": "resume", "schema": schema, "strict": True},
            },
        }
        attempt = 0
        t0 = time.monotonic()
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            while attempt <= max_retries:
                resp = await client.post(
                    f"{self.base_url}/chat/completions",
                    headers=self._headers(),
                    json={**payload, "messages": messages},
                )
                duration_ms = round((time.monotonic() - t0) * 1000)
                if resp.status_code != 200:
                    raise OpenRouterError(resp.status_code, resp.text)
                data = resp.json()
                usage = data.get("usage", {})
                content = data["choices"][0]["message"]["content"]
                log.info(
                    "openrouter_call",
                    model=self.model,
                    prompt_tokens=usage.get("prompt_tokens"),
                    completion_tokens=usage.get("completion_tokens"),
                    duration_ms=duration_ms,
                    attempt=attempt,
                    prompt_len=len(user),
                    response_len=len(content),
                )
                try:
                    return json.loads(content)
                except json.JSONDecodeError as exc:
                    attempt += 1
                    if attempt > max_retries:
                        raise OpenRouterError(200, f"Non-JSON response after {attempt} attempts: {exc}")
                    messages.append({"role": "assistant", "content": content})
                    messages.append({
                        "role": "user",
                        "content": f"Your last response was not valid JSON: {exc}. Please respond with valid JSON only.",
                    })
