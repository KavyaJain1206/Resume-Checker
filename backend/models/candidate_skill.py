from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database.base import Base

if TYPE_CHECKING:
    from models.candidate import Candidate


class CandidateSkill(Base):
    """One row per (candidate, skill). Normalized out of the comma-separated
    'skills' string so future filtering ('who knows React?') is a plain
    indexed lookup instead of a text scan."""

    __tablename__ = "candidate_skills"
    __table_args__ = (UniqueConstraint("candidate_id", "skill", name="uq_candidate_skill"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    candidate_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("candidates.id", ondelete="CASCADE"), nullable=False, index=True
    )
    skill: Mapped[str] = mapped_column(String(100), nullable=False, index=True)

    candidate: Mapped["Candidate"] = relationship(back_populates="skills")
