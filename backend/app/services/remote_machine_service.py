"""Business logic for remote machines: CRUD, connection testing, assignments,
and read-only SFTP browsing."""
from __future__ import annotations

import posixpath
from datetime import datetime, timezone
from pathlib import Path

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.ssh_crypto import encrypt_secret
from app.core.ssh_pool import HostKeyMismatchError, ssh_pool
from app.models.remote_machine import RemoteMachine, SSHAuthType
from app.models.user import User
from app.models.user_remote_machine import UserRemoteMachine
from app.schemas.remote_machine import (
    ConnectionTestResult,
    RemoteBrowseEntry,
    RemoteBrowseResult,
    RemoteMachineCreate,
    RemoteMachineUpdate,
)


# --- CRUD ---------------------------------------------------------------------


def _validate_ssh_key_path(ssh_key_path: str) -> str:
    """Confine an operator-supplied SSH key path to ``SSH_KEY_ALLOWED_DIR``.

    Resolves symlinks and ``..`` segments before checking containment so the
    SSH client can never be pointed at arbitrary files (e.g. ``/etc/shadow``).
    Returns the normalised absolute path.
    """
    allowed_root = Path(settings.SSH_KEY_ALLOWED_DIR).resolve()
    candidate = Path(ssh_key_path)
    if not candidate.is_absolute():
        candidate = allowed_root / candidate
    resolved = candidate.resolve()
    if resolved != allowed_root and allowed_root not in resolved.parents:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "ssh_key_path must be located within the configured SSH key "
                f"directory ({settings.SSH_KEY_ALLOWED_DIR})"
            ),
        )
    return str(resolved)


async def create_machine(data: RemoteMachineCreate, db: AsyncSession) -> RemoteMachine:
    existing = (
        await db.execute(select(RemoteMachine).where(RemoteMachine.name == data.name))
    ).scalar_one_or_none()
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A remote machine with this name already exists",
        )

    machine = RemoteMachine(
        name=data.name,
        host=data.host,
        port=data.port,
        username=data.username,
        auth_type=data.auth_type,
        download_folder=data.download_folder,
        is_active=data.is_active,
        encrypted_password=(
            encrypt_secret(data.password)
            if data.auth_type == SSHAuthType.password and data.password
            else None
        ),
        ssh_key_path=(
            _validate_ssh_key_path(data.ssh_key_path)
            if data.auth_type == SSHAuthType.key and data.ssh_key_path
            else None
        ),
    )
    db.add(machine)
    await db.commit()
    await db.refresh(machine)
    return machine


async def list_machines(
    db: AsyncSession, *, page: int = 1, page_size: int = 20
) -> tuple[list[RemoteMachine], int]:
    page = max(1, page)
    page_size = max(1, min(100, page_size))
    total = (
        await db.execute(select(func.count()).select_from(RemoteMachine))
    ).scalar_one()
    rows = (
        (
            await db.execute(
                select(RemoteMachine)
                .order_by(RemoteMachine.name)
                .offset((page - 1) * page_size)
                .limit(page_size)
            )
        )
        .scalars()
        .all()
    )
    return list(rows), total


async def get_machine_or_404(machine_id: int, db: AsyncSession) -> RemoteMachine:
    machine = await db.get(RemoteMachine, machine_id)
    if machine is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Remote machine not found"
        )
    return machine


async def update_machine(
    machine_id: int, data: RemoteMachineUpdate, db: AsyncSession
) -> RemoteMachine:
    machine = await get_machine_or_404(machine_id, db)

    if data.name is not None and data.name != machine.name:
        clash = (
            await db.execute(
                select(RemoteMachine).where(
                    RemoteMachine.name == data.name, RemoteMachine.id != machine_id
                )
            )
        ).scalar_one_or_none()
        if clash is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="A remote machine with this name already exists",
            )
        machine.name = data.name

    for field in ("host", "port", "username", "download_folder", "is_active"):
        value = getattr(data, field)
        if value is not None:
            setattr(machine, field, value)

    if data.auth_type is not None:
        machine.auth_type = data.auth_type
    if machine.auth_type == SSHAuthType.password:
        if data.password:
            machine.encrypted_password = encrypt_secret(data.password)
        machine.ssh_key_path = None
    else:
        if data.ssh_key_path is not None:
            machine.ssh_key_path = _validate_ssh_key_path(data.ssh_key_path)
        machine.encrypted_password = None

    # Connection parameters may have changed; drop any pooled connection and
    # require a fresh test to re-pin the host key.
    machine.host_key_fingerprint = None
    machine.updated_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(machine)
    await ssh_pool.invalidate(machine.id)
    return machine


async def delete_machine(machine_id: int, db: AsyncSession) -> None:
    machine = await get_machine_or_404(machine_id, db)
    await db.delete(machine)
    await db.commit()
    await ssh_pool.invalidate(machine_id)


# --- Connection testing -------------------------------------------------------


async def test_machine(machine_id: int, db: AsyncSession) -> ConnectionTestResult:
    machine = await get_machine_or_404(machine_id, db)
    try:
        fingerprint = await ssh_pool.test_connection(machine)
    except HostKeyMismatchError as exc:
        return ConnectionTestResult(success=False, message=str(exc))
    except Exception as exc:  # noqa: BLE001 - surface a readable error to admins
        return ConnectionTestResult(
            success=False, message=f"Connection failed: {exc}"
        )

    # Trust-On-First-Use: pin the fingerprint if not already set.
    if not machine.host_key_fingerprint:
        machine.host_key_fingerprint = fingerprint
        machine.updated_at = datetime.now(timezone.utc)
        await db.commit()
        await db.refresh(machine)

    return ConnectionTestResult(
        success=True,
        message="Connection successful",
        host_key_fingerprint=fingerprint,
    )


# --- Assignments --------------------------------------------------------------


async def list_assigned_users(
    machine_id: int, db: AsyncSession
) -> list[User]:
    await get_machine_or_404(machine_id, db)
    rows = (
        (
            await db.execute(
                select(User)
                .join(
                    UserRemoteMachine,
                    UserRemoteMachine.user_id == User.id,
                )
                .where(UserRemoteMachine.remote_machine_id == machine_id)
                .order_by(User.username)
            )
        )
        .scalars()
        .all()
    )
    return list(rows)


async def assign_user(machine_id: int, user_id: int, db: AsyncSession) -> None:
    await get_machine_or_404(machine_id, db)
    user = await db.get(User, user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )
    existing = (
        await db.execute(
            select(UserRemoteMachine).where(
                UserRemoteMachine.user_id == user_id,
                UserRemoteMachine.remote_machine_id == machine_id,
            )
        )
    ).scalar_one_or_none()
    if existing is not None:
        return
    db.add(UserRemoteMachine(user_id=user_id, remote_machine_id=machine_id))
    await db.commit()


async def unassign_user(machine_id: int, user_id: int, db: AsyncSession) -> None:
    assignment = (
        await db.execute(
            select(UserRemoteMachine).where(
                UserRemoteMachine.user_id == user_id,
                UserRemoteMachine.remote_machine_id == machine_id,
            )
        )
    ).scalar_one_or_none()
    if assignment is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Assignment not found"
        )
    await db.delete(assignment)
    await db.commit()


async def list_user_machines(user_id: int, db: AsyncSession) -> list[RemoteMachine]:
    rows = (
        (
            await db.execute(
                select(RemoteMachine)
                .join(
                    UserRemoteMachine,
                    UserRemoteMachine.remote_machine_id == RemoteMachine.id,
                )
                .where(
                    UserRemoteMachine.user_id == user_id,
                    RemoteMachine.is_active.is_(True),
                )
                .order_by(RemoteMachine.name)
            )
        )
        .scalars()
        .all()
    )
    return list(rows)


# --- Read-only browsing -------------------------------------------------------


def _resolve_browse_path(root: str, path: str | None) -> str:
    """Constrain a requested path to the machine's download folder."""
    root_norm = posixpath.normpath(root)
    rel = (path or "").strip().lstrip("/")
    target = posixpath.normpath(posixpath.join(root_norm, rel))
    if target != root_norm and not target.startswith(root_norm + "/"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Path escapes the allowed download folder",
        )
    return target


async def browse_machine(
    machine_id: int,
    user_id: int,
    path: str | None,
    db: AsyncSession,
    *,
    max_entries: int,
) -> RemoteBrowseResult:
    """List a remote directory (read-only) for an assigned user."""
    assignment = (
        await db.execute(
            select(UserRemoteMachine).where(
                UserRemoteMachine.user_id == user_id,
                UserRemoteMachine.remote_machine_id == machine_id,
            )
        )
    ).scalar_one_or_none()
    machine = await db.get(RemoteMachine, machine_id)
    # Avoid leaking machine existence to unauthorized users: 404 in both cases.
    if machine is None or assignment is None or not machine.is_active:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Remote machine not found"
        )

    target = _resolve_browse_path(machine.download_folder, path)

    conn = await ssh_pool.get_connection(machine)
    entries: list[RemoteBrowseEntry] = []
    async with conn.start_sftp_client() as sftp:
        if not await sftp.isdir(target):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Path is not a directory",
            )
        names = await sftp.listdir(target)
        for name in names:
            if name in (".", ".."):
                continue
            full = posixpath.join(target, name)
            try:
                attrs = await sftp.stat(full)
                is_dir = await sftp.isdir(full)
            except Exception:  # noqa: BLE001 - skip unreadable entries
                continue
            entries.append(
                RemoteBrowseEntry(
                    name=name,
                    type="dir" if is_dir else "file",
                    size=None if is_dir else attrs.size,
                    modified=(
                        datetime.fromtimestamp(attrs.mtime, tz=timezone.utc)
                        if attrs.mtime
                        else None
                    ),
                )
            )
            if len(entries) >= max_entries:
                break

    entries.sort(key=lambda e: (e.type != "dir", e.name.lower()))
    # Return the path relative to the configured root for the frontend.
    root_norm = posixpath.normpath(machine.download_folder)
    relative = "/" if target == root_norm else "/" + target[len(root_norm) + 1 :]
    return RemoteBrowseResult(path=relative, entries=entries)
