from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, SmallInteger, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from database.base import Base


class JdMatchAnalysis(Base):
    __tablename__ = "jd_match_analyses"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    resume_file_name: Mapped[str] = mapped_column(String(500), nullable=False)
    jd_file_name: Mapped[str] = mapped_column(String(500), nullable=False)
    resume_storage_path: Mapped[str] = mapped_column(String(1000), nullable=False)
    jd_storage_path: Mapped[str] = mapped_column(String(1000), nullable=False)
    resume_raw_extracted_text: Mapped[str] = mapped_column(Text, nullable=False, default="")
    jd_raw_extracted_text: Mapped[str] = mapped_column(Text, nullable=False, default="")

    overall_match_score: Mapped[int] = mapped_column(SmallInteger, nullable=False, index=True)
    resume_ats_score: Mapped[int] = mapped_column(SmallInteger, nullable=False, index=True)
    keyword_match_score: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    skills_match_score: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    education_match_score: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    experience_match_score: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    certification_match_score: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    responsibilities_match_score: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    projects_match_score: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)

    analysis_json: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )