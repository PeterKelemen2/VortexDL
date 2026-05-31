from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING

from sqlalchemy import Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base

if TYPE_CHECKING:
    from app.models.user import User


class AuditLog(Base):
    """Append-only record of security-relevant actions.

    Rows are never updated or deleted by the application. ``user_id`` is
    nullable and uses SET NULL on user deletion so the historical event
    survives even after the actor's account is removed.
    """

    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    # Denormalized username snapshot so the record is meaningful after deletion.
    username: Mapped[str | None] = mapped_column(String(255), nullable=True)
    # Action discriminator, e.g. "user.login", "user.password_changed".
    action: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    # Free-form, optionally JSON-encoded contextual detail.
    detail: Mapped[str | None] = mapped_column(Text, nullable=True)
    ip_address: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), index=True
    )

    user: Mapped["User | None"] = relationship("User")
