from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, SmallInteger, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database.base import Base

if TYPE_CHECKING:
    from models.audit_result import AuditResult


class AuditCategoryScore(Base):
    """9 rows per audit (one per Playbook dimension) instead of 9 columns,
    so cross-candidate aggregation (e.g. average ATS score by role) is a
    GROUP BY instead of parsing JSON in application code."""

    __tablename__ = "audit_category_scores"
    __table_args__ = (UniqueConstraint("audit_result_id", "category", name="uq_audit_category"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    audit_result_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("audit_results.id", ondelete="CASCADE"), nullable=False, index=True
    )
    category: Mapped[str] = mapped_column(String(50), nullable=False)
    score: Mapped[int] = mapped_column(SmallInteger, nullable=False)

    audit_result: Mapped["AuditResult"] = relationship(back_populates="category_scores")
