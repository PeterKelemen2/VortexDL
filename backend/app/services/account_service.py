"""Account lifecycle flows: email verification and password reset.

Token strategy: a cryptographically random URL-safe token is emailed to the
user, while only its SHA-256 hash is persisted. Incoming tokens are hashed and
matched against the stored hash, so a database leak never exposes a usable
token. Tokens are single-use and time-limited.

All "request" endpoints return a generic success response regardless of whether
the email exists, to prevent account enumeration.
"""

from __future__ import annotations

import logging
import secrets
from datetime import datetime, timedelta, timezone

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.security import hash_password
from app.models.refresh_token import RefreshToken
from app.models.user import User
from app.schemas.auth import (
    EmailVerificationConfirm,
    EmailVerificationRequest,
    MessageResponse,
    PasswordResetConfirm,
    PasswordResetRequest,
)
from app.services.auth_service import hash_token, validate_password_strength
from app.services.email_service import email_service

logger = logging.getLogger(__name__)

_GENERIC_VERIFICATION_MSG = (
    "If an account with that email exists and is not yet verified, "
    "a verification link has been sent."
)
_GENERIC_RESET_MSG = (
    "If an account with that email exists, a password reset link has been sent."
)


def _generate_token() -> tuple[str, str]:
    """Return (raw_token, token_hash)."""
    raw = secrets.token_urlsafe(32)
    return raw, hash_token(raw)


def _build_frontend_url(path: str, token: str) -> str:
    return f"{settings.FRONTEND_URL}{path}?token={token}"


async def _get_user_by_email(db: AsyncSession, email: str) -> User | None:
    stmt = select(User).where(User.email == email.strip().lower())
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def issue_email_verification(db: AsyncSession, user: User) -> None:
    """Generate, persist and email a verification token for the given user."""
    raw, token_hash = _generate_token()
    user.email_verification_token = token_hash
    user.email_verification_expires_at = datetime.now(timezone.utc) + timedelta(
        hours=settings.EMAIL_VERIFICATION_TOKEN_EXPIRE_HOURS
    )
    await db.commit()

    verify_url = _build_frontend_url("/verify-email", raw)
    try:
        await email_service.send_verification_email(user.email, user.username, verify_url)
    except Exception:  # noqa: BLE001 - never fail the caller because email is down
        logger.exception("Failed to send verification email", extra={"user_id": user.id})


async def request_email_verification(
    data: EmailVerificationRequest, db: AsyncSession
) -> MessageResponse:
    user = await _get_user_by_email(db, data.email)
    if user is not None and not user.is_verified and user.email:
        await issue_email_verification(db, user)
    return MessageResponse(msg=_GENERIC_VERIFICATION_MSG)


async def verify_email(data: EmailVerificationConfirm, db: AsyncSession) -> MessageResponse:
    token_hash = hash_token(data.token)
    now = datetime.now(timezone.utc)

    stmt = select(User).where(User.email_verification_token == token_hash)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    if user is None or user.email_verification_expires_at is None:
        from fastapi import HTTPException

        raise HTTPException(status_code=400, detail="Invalid or expired verification token")

    expires_at = user.email_verification_expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    if expires_at < now:
        from fastapi import HTTPException

        raise HTTPException(status_code=400, detail="Invalid or expired verification token")

    user.is_verified = True
    user.email_verification_token = None
    user.email_verification_expires_at = None
    await db.commit()
    return MessageResponse(msg="Email verified successfully. You can now log in.")


async def request_password_reset(
    data: PasswordResetRequest, db: AsyncSession
) -> MessageResponse:
    user = await _get_user_by_email(db, data.email)
    if user is not None and user.email:
        raw, token_hash = _generate_token()
        user.password_reset_token = token_hash
        user.password_reset_expires_at = datetime.now(timezone.utc) + timedelta(
            minutes=settings.PASSWORD_RESET_TOKEN_EXPIRE_MINUTES
        )
        await db.commit()

        reset_url = _build_frontend_url("/reset-password", raw)
        try:
            await email_service.send_password_reset_email(user.email, user.username, reset_url)
        except Exception:  # noqa: BLE001
            logger.exception("Failed to send password reset email", extra={"user_id": user.id})

    return MessageResponse(msg=_GENERIC_RESET_MSG)


async def reset_password(data: PasswordResetConfirm, db: AsyncSession) -> MessageResponse:
    from fastapi import HTTPException

    if data.new_password != data.new_password_confirm:
        raise HTTPException(status_code=400, detail="Passwords do not match")
    validate_password_strength(data.new_password)

    token_hash = hash_token(data.token)
    now = datetime.now(timezone.utc)

    stmt = select(User).where(User.password_reset_token == token_hash)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    if user is None or user.password_reset_expires_at is None:
        raise HTTPException(status_code=400, detail="Invalid or expired reset token")

    expires_at = user.password_reset_expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    if expires_at < now:
        raise HTTPException(status_code=400, detail="Invalid or expired reset token")

    user.hashed_password = hash_password(data.new_password)
    user.password_reset_token = None
    user.password_reset_expires_at = None
    # A password reset is a security event: revoke every active session.
    await db.execute(
        update(RefreshToken)
        .where(RefreshToken.user_id == user.id, RefreshToken.revoked == False)  # noqa: E712
        .values(revoked=True)
    )
    await db.commit()
    return MessageResponse(msg="Password reset successfully. You can now log in.")
