from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Optional

import structlog
from jinja2 import Environment, FileSystemLoader, select_autoescape
from playwright.async_api import Browser, Playwright, async_playwright

from cv_tailor.config import get_settings

log = structlog.get_logger(__name__)


class PDFTimeoutError(Exception):
    pass


class PDFRendererUnavailable(Exception):
    pass


_playwright: Optional[Playwright] = None
_browser: Optional[Browser] = None

_TEMPLATES_DIR = Path(__file__).parent.parent / "templates"


async def startup_pdf() -> None:
    global _playwright, _browser
    try:
        _playwright = await async_playwright().start()
        _browser = await _playwright.chromium.launch(headless=True)
        log.info("pdf_renderer_started")
    except Exception as exc:
        raise PDFRendererUnavailable(
            f"Chromium unavailable: {exc}. Run: playwright install chromium --with-deps"
        ) from exc


async def shutdown_pdf() -> None:
    global _playwright, _browser
    if _browser:
        await _browser.close()
    if _playwright:
        await _playwright.stop()
    log.info("pdf_renderer_stopped")


async def render_pdf(resume: dict, *, timeout_seconds: int | None = None) -> bytes:
    if _browser is None:
        raise PDFRendererUnavailable("Call startup_pdf() first")
    if timeout_seconds is None:
        timeout_seconds = get_settings().pdf_timeout_seconds

    if "data" in resume and isinstance(resume["data"], dict):
        resume = resume["data"]

    summary = resume.get("summary", {})
    if summary.get("content"):
        resume.setdefault("basics", {})["summary"] = summary["content"]

    env = Environment(
        loader=FileSystemLoader(str(_TEMPLATES_DIR)),
        autoescape=select_autoescape(["html"]),
    )
    tmpl = env.get_template("resume_pdf.html")
    html = tmpl.render(resume=resume)
    try:
        page = await _browser.new_page()
        try:
            await page.set_content(html, wait_until="networkidle")
            pdf_bytes = await asyncio.wait_for(
                page.pdf(format="A4", print_background=True),
                timeout=timeout_seconds,
            )
        finally:
            await page.close()
    except asyncio.TimeoutError as exc:
        raise PDFTimeoutError(f"PDF render timed out after {timeout_seconds}s") from exc
    log.info("pdf_rendered", size_bytes=len(pdf_bytes))
    return pdf_bytes
