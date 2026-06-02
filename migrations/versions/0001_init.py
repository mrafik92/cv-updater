"""init schema

Revision ID: 0001_init
Revises:
Create Date: 2026-06-02 00:00:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "0001_init"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "jobs",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("title", sa.String(), nullable=True),
        sa.Column("company", sa.String(), nullable=True),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
    )
    op.create_index("ix_jobs_created_at", "jobs", ["created_at"])

    op.create_table(
        "generations",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("job_id", sa.Integer(), sa.ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("base_resume_id", sa.String(), nullable=False),
        sa.Column("base_resume_snapshot", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
    )

    op.create_table(
        "versions",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("generation_id", sa.Integer(), sa.ForeignKey("generations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("version_number", sa.Integer(), nullable=False),
        sa.Column("resume_json", sa.Text(), nullable=False),
        sa.Column("feedback_text", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.UniqueConstraint("generation_id", "version_number", name="uq_versions_generation_version"),
    )
    op.create_index("ix_versions_generation_id", "versions", ["generation_id"])


def downgrade() -> None:
    op.drop_index("ix_versions_generation_id", table_name="versions")
    op.drop_table("versions")
    op.drop_table("generations")
    op.drop_index("ix_jobs_created_at", table_name="jobs")
    op.drop_table("jobs")
