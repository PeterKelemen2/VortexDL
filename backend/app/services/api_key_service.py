"""Business logic for user-owned API keys: creation, listing, revocation, auth."""
from __future__ import annotations

import secrets
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.api_key import ApiKey
from app.models.user import User
from app.schemas.api_key import ApiKeyCreate
from app.services.auth_service import hash_token

KEY_PREFIX = "ytk_"


def _generate_key() -> tuple[str, str]:
    """Return (plaintext_key, prefix). Plaintext is shown to the user once."""
    body = secrets.token_urlsafe(32)
    plaintext = f"{KEY_PREFIX}{body}"
    # Store a short, non-secret identifier prefix for display.
    prefix = plaintext[: len(KEY_PREFIX) + 8]
    return plaintext, prefix


async def create_api_key(
    data: ApiKeyCreate, user_id: int, db: AsyncSession
) -> tuple[ApiKey, str]:
    plaintext, prefix = _generate_key()
    expires_at = None
    if data.expires_in_days is not None:
        expires_at = datetime.now(timezone.utc) + timedelta(days=data.expires_in_days)

    api_key = ApiKey(
        user_id=user_id,
        name=data.name,
        prefix=prefix,
        key_hash=hash_token(plaintext),
        expires_at=expires_at,
    )
    db.add(api_key)
    await db.commit()
    await db.refresh(api_key)
    from app.services.audit_service import AuditAction, record_event

    await record_event(
        db,
        action=AuditAction.API_KEY_CREATED,
        user_id=user_id,
        detail=f"name={api_key.name}, prefix={api_key.prefix}",
    )
    return api_key, plaintext


async def list_api_keys(user_id: int, db: AsyncSession) -> list[ApiKey]:
    stmt = (
        select(ApiKey)
        .where(ApiKey.user_id == user_id)
        .order_by(ApiKey.created_at.desc())
    )
    return list((await db.execute(stmt)).scalars().all())


async def revoke_api_key(key_id: int, user_id: int, db: AsyncSession) -> None:
    api_key = await db.get(ApiKey, key_id)
    if api_key is None or api_key.user_id != user_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="API key not found")
    if api_key.revoked:
        return
    api_key.revoked = True
    await db.commit()
    from app.services.audit_service import AuditAction, record_event

    await record_event(
        db,
        action=AuditAction.API_KEY_REVOKED,
        user_id=user_id,
        detail=f"name={api_key.name}, prefix={api_key.prefix}",
    )


async def resolve_api_key(raw_key: str, db: AsyncSession) -> User | None:
    """Authenticate a request by its raw API key. Updates last_used_at on success."""
    if not raw_key or not raw_key.startswith(KEY_PREFIX):
        return None
    key_hash = hash_token(raw_key)
    stmt = select(ApiKey).where(ApiKey.key_hash == key_hash, ApiKey.revoked == False)
    api_key = (await db.execute(stmt)).scalar_one_or_none()
    if api_key is None:
        return None
    if api_key.expires_at is not None and api_key.expires_at <= datetime.now(timezone.utc):
        return None

    api_key.last_used_at = datetime.now(timezone.utc)
    await db.commit()

    return await db.get(User, api_key.user_id)
