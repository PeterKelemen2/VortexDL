"""Append-only audit logging of security-relevant events."""
from __future__ import annotations

import logging

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit_log import AuditLog
from app.models.user import User

logger = logging.getLogger("app.audit")


# Canonical action identifiers.
class AuditAction:
    LOGIN = "user.login"
    LOGOUT = "user.logout"
    REGISTER = "user.register"
    PASSWORD_CHANGED = "user.password_changed"
    PASSWORD_RESET = "user.password_reset"
    EMAIL_VERIFIED = "user.email_verified"
    TWO_FACTOR_ENABLED = "user.2fa_enabled"
    TWO_FACTOR_DISABLED = "user.2fa_disabled"
    API_KEY_CREATED = "user.api_key_created"
    API_KEY_REVOKED = "user.api_key_revoked"
    ADMIN_USER_UPDATED = "admin.user_updated"
    ADMIN_USER_DELETED = "admin.user_deleted"


async def record_event(
    db: AsyncSession,
    *,
    action: str,
    user_id: int | None = None,
    username: str | None = None,
    detail: str | None = None,
    ip_address: str | None = None,
    commit: bool = True,
) -> None:
    """Persist an audit event. Never raises into the caller's request path."""
    try:
        entry = AuditLog(
            user_id=user_id,
            username=username,
            action=action,
            detail=detail,
            ip_address=ip_address,
        )
        db.add(entry)
        if commit:
            await db.commit()
    except Exception:  # noqa: BLE001 - auditing must not break the main action
        logger.exception("Failed to record audit event '%s'", action)
        if commit:
            await db.rollback()


async def list_events(
    db: AsyncSession,
    *,
    page: int = 1,
    page_size: int = 50,
    action: str | None = None,
    user_id: int | None = None,
) -> tuple[list[AuditLog], int]:
    page = max(1, page)
    page_size = max(1, min(200, page_size))

    base = select(AuditLog)
    count_stmt = select(func.count()).select_from(AuditLog)
    if action:
        base = base.where(AuditLog.action == action)
        count_stmt = count_stmt.where(AuditLog.action == action)
    if user_id is not None:
        base = base.where(AuditLog.user_id == user_id)
        count_stmt = count_stmt.where(AuditLog.user_id == user_id)

    total = (await db.execute(count_stmt)).scalar_one()
    stmt = (
        base.order_by(AuditLog.created_at.desc(), AuditLog.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    rows = (await db.execute(stmt)).scalars().all()
    return list(rows), total
