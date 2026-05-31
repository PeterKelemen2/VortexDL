from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Integer, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base

if TYPE_CHECKING:
    from app.models.remote_machine import RemoteMachine
    from app.models.user import User


class UserRemoteMachine(Base):
    """Association granting a user access to a remote machine (1:n per user).

    A user may be assigned to many machines; each row is a single grant. The
    unique constraint prevents duplicate assignments.
    """

    __tablename__ = "user_remote_machines"
    __table_args__ = (
        UniqueConstraint(
            "user_id", "remote_machine_id", name="uq_user_remote_machine"
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    remote_machine_id: Mapped[int] = mapped_column(
        ForeignKey("remote_machines.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    user: Mapped["User"] = relationship("User")
    remote_machine: Mapped["RemoteMachine"] = relationship(
        "RemoteMachine", back_populates="assignments"
    )
