from __future__ import annotations

from collections.abc import Generator

from sqlalchemy import select
from sqlalchemy.orm import Session

from cv_tailor.db import engine
from cv_tailor.models import Generation, Job, Version


def get_db() -> Generator[Session, None, None]:
    with Session(engine) as session:
        yield session


def create_job(db: Session, *, title: str | None, company: str | None, description: str) -> Job:
    job = Job(title=title, company=company, description=description)
    db.add(job)
    db.flush()
    return job


def get_or_create_generation(
    db: Session, *, job_id: int, base_resume_id: str, base_resume_snapshot: dict
) -> Generation:
    stmt = select(Generation).where(
        Generation.job_id == job_id,
        Generation.base_resume_id == base_resume_id,
    )
    gen = db.execute(stmt).scalar_one_or_none()
    if gen is None:
        gen = Generation(
            job_id=job_id,
            base_resume_id=base_resume_id,
            base_resume_snapshot=base_resume_snapshot,
        )
        db.add(gen)
        db.flush()
    return gen


def add_version(
    db: Session, *, generation_id: int, resume_json: dict, feedback_text: str | None = None
) -> Version:
    stmt = select(Version).where(Version.generation_id == generation_id).order_by(Version.version_number.desc())
    last = db.execute(stmt).first()
    next_num = (last[0].version_number + 1) if last else 1
    version = Version(
        generation_id=generation_id,
        version_number=next_num,
        resume_json=resume_json,
        feedback_text=feedback_text,
    )
    db.add(version)
    db.flush()
    return version


def list_versions(db: Session, *, generation_id: int) -> list[Version]:
    stmt = (
        select(Version)
        .where(Version.generation_id == generation_id)
        .order_by(Version.version_number.asc())
    )
    return list(db.execute(stmt).scalars().all())


def get_version(db: Session, version_id: int) -> Version | None:
    return db.get(Version, version_id)


def cumulative_feedback(db: Session, *, generation_id: int) -> list[str]:
    versions = list_versions(db, generation_id=generation_id)
    return [v.feedback_text for v in versions if v.feedback_text]


def list_generations(db: Session, *, job_id: int) -> list[Generation]:
    stmt = select(Generation).where(Generation.job_id == job_id)
    return list(db.execute(stmt).scalars().all())


def list_jobs(db: Session) -> list[Job]:
    stmt = select(Job).order_by(Job.created_at.desc())
    return list(db.execute(stmt).scalars().all())
