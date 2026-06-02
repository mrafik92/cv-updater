from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, Text, UniqueConstraint, text
from sqlalchemy.dialects.sqlite import JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from cv_tailor.db import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Job(Base):
    __tablename__ = "jobs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    title: Mapped[str | None] = mapped_column(String, nullable=True)
    company: Mapped[str | None] = mapped_column(String, nullable=True)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, server_default=text("CURRENT_TIMESTAMP"), nullable=False
    )

    generations: Mapped[list["Generation"]] = relationship(back_populates="job", cascade="all, delete-orphan")


class Generation(Base):
    __tablename__ = "generations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    job_id: Mapped[int] = mapped_column(ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False)
    base_resume_id: Mapped[str] = mapped_column(String, nullable=False)
    base_resume_snapshot: Mapped[dict] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, server_default=text("CURRENT_TIMESTAMP"), nullable=False
    )

    job: Mapped[Job] = relationship(back_populates="generations")
    versions: Mapped[list["Version"]] = relationship(back_populates="generation", cascade="all, delete-orphan")


class Version(Base):
    __tablename__ = "versions"
    __table_args__ = (UniqueConstraint("generation_id", "version_number", name="uq_versions_generation_version"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    generation_id: Mapped[int] = mapped_column(ForeignKey("generations.id", ondelete="CASCADE"), nullable=False)
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    resume_json: Mapped[dict] = mapped_column(JSON, nullable=False)
    feedback_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, server_default=text("CURRENT_TIMESTAMP"), nullable=False
    )

    generation: Mapped[Generation] = relationship(back_populates="versions")


Index("ix_jobs_created_at", Job.created_at)
Index("ix_versions_generation_id", Version.generation_id)
