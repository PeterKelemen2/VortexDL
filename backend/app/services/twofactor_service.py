"""Service layer for managing a user's two-factor authentication settings."""
from __future__ import annotations

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import verify_password
from app.models.user import User
from app.services import totp_service


async def start_setup(user: User, db: AsyncSession) -> dict:
    """Generate a fresh (pending) secret + backup codes. Not enabled until verified."""
    if user.totp_enabled:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Two-factor authentication is already enabled",
        )

    secret = totp_service.generate_secret()
    plaintext_codes, hashed_json = totp_service.generate_backup_codes()
    account_name = user.email or user.username
    uri = totp_service.provisioning_uri(secret, account_name)

    user.totp_secret = secret
    user.totp_backup_codes = hashed_json
    user.totp_enabled = False
    await db.commit()

    return {
        "secret": secret,
        "otpauth_uri": uri,
        "qr_code": totp_service.qr_data_uri(uri),
        "backup_codes": plaintext_codes,
    }


async def confirm_setup(user: User, code: str, db: AsyncSession) -> None:
    if user.totp_enabled:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Two-factor authentication is already enabled",
        )
    if not user.totp_secret:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No pending two-factor setup. Start setup first.",
        )
    if not totp_service.verify_code(user.totp_secret, code):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid authentication code",
        )
    user.totp_enabled = True
    await db.commit()
    from app.services.audit_service import AuditAction, record_event

    await record_event(
        db, action=AuditAction.TWO_FACTOR_ENABLED, user_id=user.id, username=user.username
    )


async def disable(user: User, password: str, db: AsyncSession) -> None:
    if not user.totp_enabled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Two-factor authentication is not enabled",
        )
    # Require the account password to disable 2FA.
    if not verify_password(password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Incorrect password",
        )
    user.totp_enabled = False
    user.totp_secret = None
    user.totp_backup_codes = None
    await db.commit()
    from app.services.audit_service import AuditAction, record_event

    await record_event(
        db, action=AuditAction.TWO_FACTOR_DISABLED, user_id=user.id, username=user.username
    )


async def regenerate_backup_codes(user: User, code: str, db: AsyncSession) -> list[str]:
    if not user.totp_enabled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Two-factor authentication is not enabled",
        )
    if not totp_service.verify_code(user.totp_secret, code):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid authentication code",
        )
    plaintext_codes, hashed_json = totp_service.generate_backup_codes()
    user.totp_backup_codes = hashed_json
    await db.commit()
    return plaintext_codes
