from __future__ import annotations

import structlog
from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from cv_tailor.config import get_settings
from cv_tailor.models import Generation
from cv_tailor.schemas.job import JobInput
from cv_tailor.services.openrouter import OpenRouterClient, OpenRouterError
from cv_tailor.services.repo import (
    add_version,
    create_job,
    cumulative_feedback,
    get_db,
    get_or_create_generation,
)
from cv_tailor.services.rr_client import RRClient, RRClientError
from cv_tailor.services.tailor import FabricationError, tailor

log = structlog.get_logger(__name__)
router = APIRouter()
templates = Jinja2Templates(directory="cv_tailor/templates")


def _make_rr_client() -> RRClient:
    s = get_settings()
    return RRClient(base_url=str(s.rr_base_url), api_token=s.rr_api_token.get_secret_value())


def _make_or_client() -> OpenRouterClient:
    s = get_settings()
    return OpenRouterClient(
        api_key=s.openrouter_api_key.get_secret_value(),
        base_url=str(s.openrouter_base_url),
        model=s.openrouter_model,
    )


@router.post("/generate", response_class=HTMLResponse)
async def generate(
    request: Request,
    job_description: str = Form(...),
    base_resume_id: str = Form(...),
    generation_id: int | None = Form(None),
    feedback: str | None = Form(None),
    db: Session = Depends(get_db),
):
    rr = _make_rr_client()
    or_client = _make_or_client()

    try:
        # 1. Fetch base resume from RR
        base_resume = await rr.get_resume(base_resume_id)

        # 2. Create or load job + generation
        if generation_id is None:
            job = create_job(db, title=None, company=None, description=job_description)
            db.commit()
            gen = get_or_create_generation(
                db,
                job_id=job.id,
                base_resume_id=base_resume_id,
                base_resume_snapshot=base_resume,
            )
            db.commit()
        else:
            gen = db.get(Generation, generation_id)
            if gen is None:
                return templates.TemplateResponse(
                    request,
                    "_partials/generate_result.html",
                    {"error": "Generation not found", "version": None},
                    status_code=404,
                )
            base_resume = gen.base_resume_snapshot

        # 3. Collect cumulative feedback
        prior_feedback = cumulative_feedback(db, generation_id=gen.id)
        if feedback:
            prior_feedback = prior_feedback + [feedback]

        # 4. Call tailor
        job_input = JobInput(description=job_description)
        tailored = await tailor(or_client, base_resume, job_input, prior_feedback)

        # 5. Save version
        version = add_version(
            db,
            generation_id=gen.id,
            resume_json=tailored,
            feedback_text=feedback,
        )
        db.commit()

        log.info(
            "generate_success",
            generation_id=gen.id,
            version_id=version.id,
            version_number=version.version_number,
        )

        return templates.TemplateResponse(
            request,
            "_partials/generate_result.html",
            {
                "version": version,
                "generation": gen,
                "error": None,
            },
        )

    except RRClientError as exc:
        log.warning("rr_error", error=str(exc))
        return templates.TemplateResponse(
            request,
            "_partials/generate_result.html",
            {"error": f"Could not fetch resume from Reactive Resume: {exc}", "version": None},
            status_code=502,
        )
    except FabricationError as exc:
        log.warning("fabrication_detected", error=str(exc))
        return templates.TemplateResponse(
            request, "_partials/generate_result.html",
            {"error": f"Generation rejected: AI added content not in your original resume. Please try again. ({exc})", "version": None},
            status_code=422,
        )
    except OpenRouterError as exc:
        log.warning("openrouter_error", error=str(exc))
        return templates.TemplateResponse(
            request,
            "_partials/generate_result.html",
            {"error": f"AI generation failed: {exc}", "version": None},
            status_code=502,
        )
    except Exception as exc:
        log.exception("generate_unexpected_error", error=str(exc))
        return templates.TemplateResponse(
            request,
            "_partials/generate_result.html",
            {"error": f"Unexpected error: {exc}", "version": None},
            status_code=500,
        )
