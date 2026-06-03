from __future__ import annotations

import structlog
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from cv_tailor.config import get_settings
from cv_tailor.services.repo import get_db, get_version
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


@router.post("/push/{version_id}")
async def push_version(version_id: int, db: Session = Depends(get_db)):
    version = get_version(db, version_id)
    if version is None:
        return {"error": f"Version {version_id} not found"}

    gen = version.generation
    base_resume_id = gen.base_resume_id if gen else None

    s = get_settings()
    rr = RRClient(
        base_url=str(s.rr_base_url),
        api_token=s.rr_api_token.get_secret_value(),
    )

    try:
        if base_resume_id:
            result = await rr.update_resume(base_resume_id, version.resume_json)
            return {"success": True, "action": "updated", "id": base_resume_id}
        else:
            name = f"Tailored Resume v{version.version_number}"
            slug = f"tailored-v{version.version_number}"
            new_id = await rr.create_resume(name, slug, version.resume_json)
            return {"success": True, "action": "created", "id": new_id}
    except RRClientError as exc:
        log.warning("rr_push_error", error=str(exc), version_id=version_id)
        return {"error": str(exc)}
