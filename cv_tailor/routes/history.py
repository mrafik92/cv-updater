from __future__ import annotations

import structlog
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import select
from sqlalchemy.orm import Session

from cv_tailor.models import Generation, Job
from cv_tailor.services.repo import get_db, get_version, list_jobs, list_versions

log = structlog.get_logger(__name__)
router = APIRouter()
templates = Jinja2Templates(directory="cv_tailor/templates")


@router.get("/history", response_class=HTMLResponse)
async def history_page(request: Request, db: Session = Depends(get_db)):
    jobs = list_jobs(db)
    enriched = []
    for job in jobs:
        gens = db.execute(select(Generation).where(Generation.job_id == job.id)).scalars().all()
        for gen in gens:
            versions = list_versions(db, generation_id=gen.id)
            enriched.append({
                "job": job,
                "generation": gen,
                "version_count": len(versions),
                "latest_version": versions[-1] if versions else None,
            })
    return templates.TemplateResponse(
        request, "history.html", {"items": enriched}
    )


@router.get("/version/{version_id}", response_class=HTMLResponse)
async def version_detail(version_id: int, request: Request, db: Session = Depends(get_db)):
    version = get_version(db, version_id)
    if version is None:
        raise HTTPException(status_code=404, detail="Version not found")
    generation = db.get(Generation, version.generation_id)
    job = db.get(Job, generation.job_id)
    versions = list_versions(db, generation_id=generation.id)
    return templates.TemplateResponse(
        request,
        "version_detail.html",
        {"version": version, "generation": generation, "job": job, "all_versions": versions},
    )
