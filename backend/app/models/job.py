from __future__ import annotations

import enum
from datetime import datetime, timezone
from typing import TYPE_CHECKING

from sqlalchemy import (
    Integer,
    String,
    Text,
    ForeignKey,
    DateTime,
    Enum as SAEnum,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base

if TYPE_CHECKING:
    from app.models.user import User


class JobStatus(str, enum.Enum):
    """Lifecycle states for a background job."""

    queued = "queued"
    running = "running"
    finished = "finished"
    failed = "failed"
    canceled = "canceled"

    @property
    def is_terminal(self) -> bool:
        return self in {JobStatus.finished, JobStatus.failed, JobStatus.canceled}


class Job(Base):
    """A unit of background work tracked per user (e.g. a yt-dlp download)."""

    __tablename__ = "jobs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )

    # Discriminator so the queue can dispatch to the correct handler.
    job_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    status: Mapped[JobStatus] = mapped_column(
        SAEnum(JobStatus, native_enum=False, length=20),
        nullable=False,
        default=JobStatus.queued,
        index=True,
    )

    # The request payload (e.g. {"url": "...", "format": "..."}), JSON-encoded.
    payload: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Successful result (JSON-encoded), populated when status == finished.
    result: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Human-readable failure reason, populated when status == failed.
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Integer progress 0-100 for long-running work.
    progress: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    finished_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    user: Mapped["User"] = relationship("User")
