from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database.base import Base

if TYPE_CHECKING:
    from models.candidate import Candidate


class ResumeUpload(Base):
    """The uploaded PDF's metadata. The binary itself stays on the VPS
    filesystem (storage_path) rather than as a bytea column — standard
    practice for a single-server deployment; the DB only needs to know
    where to find it and what was extracted from it."""

    __tablename__ = "resume_uploads"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    candidate_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("candidates.id", ondelete="CASCADE"),
        nullable=False, unique=True, index=True,
    )
    file_name: Mapped[str] = mapped_column(String(500), nullable=False)
    storage_path: Mapped[str] = mapped_column(String(1000), nullable=False)
    raw_extracted_text: Mapped[str] = mapped_column(Text, nullable=False, default="")
    uploaded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    candidate: Mapped["Candidate"] = relationship(back_populates="resume_upload")
