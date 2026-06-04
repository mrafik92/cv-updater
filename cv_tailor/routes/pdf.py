from __future__ import annotations

import structlog
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from sqlalchemy.orm import Session

from cv_tailor.services.pdf import PDFRendererUnavailable, PDFTimeoutError, render_pdf
from cv_tailor.services.repo import get_db, get_version

log = structlog.get_logger(__name__)
router = APIRouter()


@router.get("/pdf/{version_id}")
async def get_pdf(version_id: int, db: Session = Depends(get_db)):
    version = get_version(db, version_id)
    if version is None:
        raise HTTPException(status_code=404, detail=f"Version {version_id} not found")

    try:
        pdf_bytes = await render_pdf(version.resume_json)
    except PDFTimeoutError as exc:
        log.warning("pdf_timeout", version_id=version_id, error=str(exc))
        raise HTTPException(status_code=504, detail="PDF rendering timed out") from exc
    except PDFRendererUnavailable as exc:
        log.error("pdf_unavailable", version_id=version_id, error=str(exc))
        raise HTTPException(status_code=503, detail="PDF renderer unavailable") from exc

    filename = f"resume_v{version.version_number}.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="{filename}"'},
    )
