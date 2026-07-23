"""add jd match analyses

Revision ID: 7d8d5c3d8d01
Revises: e2e1eb75e9ee
Create Date: 2026-07-23 00:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = '7d8d5c3d8d01'
down_revision: Union[str, None] = 'e2e1eb75e9ee'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "jd_match_analyses",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("resume_file_name", sa.String(500), nullable=False),
        sa.Column("jd_file_name", sa.String(500), nullable=False),
        sa.Column("resume_storage_path", sa.String(1000), nullable=False),
        sa.Column("jd_storage_path", sa.String(1000), nullable=False),
        sa.Column("resume_raw_extracted_text", sa.Text(), nullable=False, server_default=""),
        sa.Column("jd_raw_extracted_text", sa.Text(), nullable=False, server_default=""),
        sa.Column("overall_match_score", sa.SmallInteger(), nullable=False),
        sa.Column("resume_ats_score", sa.SmallInteger(), nullable=False),
        sa.Column("keyword_match_score", sa.SmallInteger(), nullable=False),
        sa.Column("skills_match_score", sa.SmallInteger(), nullable=False),
        sa.Column("education_match_score", sa.SmallInteger(), nullable=False),
        sa.Column("experience_match_score", sa.SmallInteger(), nullable=False),
        sa.Column("certification_match_score", sa.SmallInteger(), nullable=False),
        sa.Column("responsibilities_match_score", sa.SmallInteger(), nullable=False),
        sa.Column("projects_match_score", sa.SmallInteger(), nullable=True),
        sa.Column("analysis_json", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_jd_match_analyses_overall_match_score", "jd_match_analyses", ["overall_match_score"])
    op.create_index("ix_jd_match_analyses_resume_ats_score", "jd_match_analyses", ["resume_ats_score"])
    op.create_index("ix_jd_match_analyses_created_at", "jd_match_analyses", ["created_at"])


def downgrade() -> None:
    op.drop_table("jd_match_analyses")