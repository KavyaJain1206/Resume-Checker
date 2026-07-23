from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import DateTime, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database.base import Base

if TYPE_CHECKING:
    from models.audit_result import AuditResult
    from models.candidate_skill import CandidateSkill
    from models.resume_upload import ResumeUpload


class Candidate(Base):
    """Root entity: one row per intake submission (profile + academic fields)."""

    __tablename__ = "candidates"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    full_name: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    email: Mapped[str] = mapped_column(String(255), nullable=False, default="", index=True)
    phone: Mapped[str] = mapped_column(String(50), nullable=False, default="")
    location: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    college: Mapped[str] = mapped_column(String(255), nullable=False, default="", index=True)
    degree: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    branch: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    grad_year: Mapped[str] = mapped_column(String(20), nullable=False, default="")
    cgpa: Mapped[str] = mapped_column(String(20), nullable=False, default="")
    target_role: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    experience_level: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    linkedin_url: Mapped[str] = mapped_column(String(500), nullable=False, default="")
    github_url: Mapped[str] = mapped_column(String(500), nullable=False, default="")

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    skills: Mapped[List["CandidateSkill"]] = relationship(
        back_populates="candidate", cascade="all, delete-orphan", passive_deletes=True,
        order_by="CandidateSkill.skill",
    )
    resume_upload: Mapped[Optional["ResumeUpload"]] = relationship(
        back_populates="candidate", cascade="all, delete-orphan", passive_deletes=True,
        uselist=False,
    )
    audit_results: Mapped[List["AuditResult"]] = relationship(
        back_populates="candidate", cascade="all, delete-orphan", passive_deletes=True,
        order_by="AuditResult.created_at.desc()",
    )
