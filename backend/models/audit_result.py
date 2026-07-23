from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, List

from sqlalchemy import DateTime, ForeignKey, SmallInteger, String, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database.base import Base

if TYPE_CHECKING:
    from models.audit_category_score import AuditCategoryScore
    from models.audit_finding import AuditFinding
    from models.candidate import Candidate


class AuditResult(Base):
    """One row per diagnostic run. Kept separate from candidates (rather
    than columns on it) so a future re-audit is a new row, not a
    destructive overwrite — audit history for free.

    keyword_gaps / passed_checks stay JSONB: small, display-only, never
    filtered or joined against by the app today."""

    __tablename__ = "audit_results"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    candidate_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("candidates.id", ondelete="CASCADE"), nullable=False, index=True
    )

    overall_score: Mapped[int] = mapped_column(SmallInteger, nullable=False, index=True)
    recruiter_7sec_scan: Mapped[str] = mapped_column(String(10), nullable=False, index=True)
    ats_risk_level: Mapped[str] = mapped_column(String(10), nullable=False, index=True)

    keyword_gaps: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    passed_checks: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)

    bullet_count: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=0)
    page_count: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=0)
    file_name: Mapped[str] = mapped_column(String(500), nullable=False, default="")

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )

    candidate: Mapped["Candidate"] = relationship(back_populates="audit_results")
    category_scores: Mapped[List["AuditCategoryScore"]] = relationship(
        back_populates="audit_result", cascade="all, delete-orphan", passive_deletes=True,
    )
    findings: Mapped[List["AuditFinding"]] = relationship(
        back_populates="audit_result", cascade="all, delete-orphan", passive_deletes=True,
        order_by="AuditFinding.sort_order",
    )
