from __future__ import annotations

import enum
from datetime import datetime, timezone
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum as SAEnum,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base

if TYPE_CHECKING:
    from app.models.user_remote_machine import UserRemoteMachine


class SSHAuthType(str, enum.Enum):
    """Authentication mechanism used to connect to a remote machine."""

    password = "password"
    key = "key"


class RemoteMachine(Base):
    """An SSH/SFTP-reachable target where downloads can be delivered.

    Managed by administrators. Regular users may only use a machine if they
    have been explicitly assigned to it (see :class:`UserRemoteMachine`).
    """

    __tablename__ = "remote_machines"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False, unique=True)
    host: Mapped[str] = mapped_column(String(255), nullable=False)
    port: Mapped[int] = mapped_column(Integer, nullable=False, default=22)
    username: Mapped[str] = mapped_column(String(128), nullable=False)

    auth_type: Mapped[SSHAuthType] = mapped_column(
        SAEnum(SSHAuthType, native_enum=False, length=16),
        nullable=False,
        default=SSHAuthType.password,
    )
    # Fernet-encrypted password (auth_type == password). Never stored plaintext.
    encrypted_password: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Server-side path to a private key file (auth_type == key).
    ssh_key_path: Mapped[str | None] = mapped_column(String(1024), nullable=True)

    # Root directory on the remote host that downloads are written into and that
    # users may browse (read-only). All paths are constrained to this prefix.
    download_folder: Mapped[str] = mapped_column(String(1024), nullable=False)

    # Trust-on-first-use host key fingerprint, captured during a connection test.
    host_key_fingerprint: Mapped[str | None] = mapped_column(String(512), nullable=True)

    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    assignments: Mapped[list["UserRemoteMachine"]] = relationship(
        "UserRemoteMachine",
        back_populates="remote_machine",
        cascade="all, delete-orphan",
    )
