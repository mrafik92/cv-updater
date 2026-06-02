from __future__ import annotations

import structlog
from fastapi import APIRouter

from cv_tailor.config import get_settings
from cv_tailor.services.rr_client import RRClient, RRClientError

log = structlog.get_logger(__name__)
router = APIRouter()


@router.get("/resumes")
async def list_resumes():
    s = get_settings()
    rr = RRClient(
        base_url=str(s.rr_base_url),
        api_token=s.rr_api_token.get_secret_value(),
    )
    try:
        resumes = await rr.list_resumes()
        return {"resumes": resumes}
    except RRClientError as exc:
        log.warning("rr_list_resumes_error", error=str(exc))
        return {"resumes": [], "error": str(exc)}
