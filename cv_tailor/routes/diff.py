from __future__ import annotations

import structlog
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from cv_tailor.services.diff import compute_diff
from cv_tailor.services.repo import get_db, get_version

log = structlog.get_logger(__name__)
router = APIRouter()
templates = Jinja2Templates(directory="cv_tailor/templates")


@router.get("/diff/{version_a_id}/{version_b_id}", response_class=HTMLResponse)
async def diff_view(
    version_a_id: int,
    version_b_id: int,
    request: Request,
    db: Session = Depends(get_db),
):
    va = get_version(db, version_a_id)
    vb = get_version(db, version_b_id)
    if va is None or vb is None:
        raise HTTPException(status_code=404, detail="One or both versions not found")
    result = compute_diff(va.resume_json, vb.resume_json)
    return templates.TemplateResponse(request, "diff.html", {
        "version_a": va,
        "version_b": vb,
        "diff": result,
    })
