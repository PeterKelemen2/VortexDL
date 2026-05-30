from __future__ import annotations

from typing import TYPE_CHECKING
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import String, Integer, ForeignKey, DateTime
from datetime import datetime, timezone
from app.core.db import Base

if TYPE_CHECKING:
    from app.models.refresh_token import RefreshToken
    from app.models.role import Role
    from app.models.user_image import UserImage

class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    username: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    email: Mapped[str | None] = mapped_column(String(255), unique=True)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    role_id: Mapped[int] = mapped_column(ForeignKey("roles.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    role: Mapped["Role"] = relationship("Role", back_populates="users")
    refresh_tokens: Mapped[list["RefreshToken"]] = relationship("RefreshToken", back_populates="user")
    images: Mapped[list["UserImage"]] = relationship(
        "UserImage",
        back_populates="user",
        order_by="UserImage.created_at",
    )
