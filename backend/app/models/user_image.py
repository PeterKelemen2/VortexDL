from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING
from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Float
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.config import settings
from app.core.db import Base

if TYPE_CHECKING:
    from app.models.user import User


class UserImage(Base):
    __tablename__ = "user_images"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    file_path: Mapped[str] = mapped_column(String(255), nullable=False)
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    mime_type: Mapped[str] = mapped_column(String(50), nullable=False)
    avatar_path: Mapped[str | None] = mapped_column(String(255), nullable=True)
    thumbnail_path: Mapped[str | None] = mapped_column(String(255), nullable=True)
    preview_path: Mapped[str | None] = mapped_column(String(255), nullable=True)
    original_width: Mapped[int | None] = mapped_column(Integer, nullable=True)
    original_height: Mapped[int | None] = mapped_column(Integer, nullable=True)
    crop_x: Mapped[float | None] = mapped_column(Float, nullable=True)
    crop_y: Mapped[float | None] = mapped_column(Float, nullable=True)
    crop_size: Mapped[float | None] = mapped_column(Float, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    user: Mapped["User"] = relationship("User", back_populates="images")

    @property
    def url(self) -> str:
        base = settings.PROFILE_IMAGE_URL_PATH.rstrip('/')
        return f"{base}/{self.file_path}"

    def _variant_path(self, variant: str) -> str:
        original = Path(self.file_path)
        suffix = f"{settings.PROFILE_IMAGE_VARIANT_SEPARATOR}{variant}"
        return str(original.with_name(f"{original.stem}{suffix}{original.suffix}"))

    def _url_for_path(self, path: str) -> str:
        base = settings.PROFILE_IMAGE_URL_PATH.rstrip('/')
        return f"{base}/{path}"

    @property
    def avatar_url(self) -> str:
        path = self.avatar_path or self._variant_path("avatar")
        return self._url_for_path(path)

    @property
    def thumbnail_url(self) -> str:
        path = self.thumbnail_path or self._variant_path("thumbnail")
        return self._url_for_path(path)

    @property
    def preview_url(self) -> str:
        path = self.preview_path or self._variant_path("preview")
        return self._url_for_path(path)
