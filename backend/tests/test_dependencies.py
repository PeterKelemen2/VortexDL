import pytest
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from sqlalchemy import select, text

from jose import JWTError
from fastapi import HTTPException

from app.core.config import settings
from app.core.db import async_session
from app.core.security import create_access_token, hash_password
from app.models.refresh_token import RefreshToken
from app.models.role import Role
from app.models.user import User
from app.services.auth_service import hash_token
from app.core.dependencies import get_current_user, require_role


@pytest.mark.asyncio
async def test_get_current_user_with_valid_token_and_sid_sets_current_session_id():
    async with async_session() as session:
        await session.execute(text("DELETE FROM refresh_tokens"))
        await session.execute(text("DELETE FROM users"))
        await session.execute(text("DELETE FROM roles"))
        await session.commit()

        role = Role(name="user", description="Default user role")
        session.add(role)
        await session.commit()
        await session.refresh(role)

        user = User(
            username="depuser",
            email="dep@example.com",
            hashed_password=hash_password("Password123!"),
            role=role,
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)

        refresh_token = RefreshToken(
            user_id=user.id,
            token_hash=hash_token("session"),
            expires_at=datetime.now(timezone.utc) + timedelta(days=1),
            revoked=False,
        )
        session.add(refresh_token)
        await session.commit()
        await session.refresh(refresh_token)

        token = create_access_token(
            data={"sub": str(user.id), "role": "user", "sid": refresh_token.id},
            secret=settings.JWT_SECRET,
            expires_delta=timedelta(minutes=15),
            issuer=settings.JWT_ISSUER,
            audience=settings.JWT_AUDIENCE,
            algorithm=settings.JWT_ALGORITHM,
        )

        result = await get_current_user(token=token, db=session)
        assert result.id == user.id
        assert getattr(result, "current_session_id") == refresh_token.id


@pytest.mark.asyncio
async def test_get_current_user_missing_sub_raises_401():
    async with async_session() as session:
        token = create_access_token(
            data={"role": "user"},
            secret=settings.JWT_SECRET,
            expires_delta=timedelta(minutes=15),
            issuer=settings.JWT_ISSUER,
            audience=settings.JWT_AUDIENCE,
            algorithm=settings.JWT_ALGORITHM,
        )

        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(token=token, db=session)

        assert exc_info.value.status_code == 401


@pytest.mark.asyncio
async def test_get_current_user_with_invalid_sid_raises_401():
    async with async_session() as session:
        await session.execute(text("DELETE FROM users"))
        await session.execute(text("DELETE FROM roles"))
        await session.commit()

        role = Role(name="user", description="Default user role")
        session.add(role)
        await session.commit()
        await session.refresh(role)

        user = User(
            username="siduser",
            email="sid@example.com",
            hashed_password=hash_password("Password123!"),
            role=role,
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)

        token = create_access_token(
            data={"sub": str(user.id), "role": "user", "sid": "not-an-int"},
            secret=settings.JWT_SECRET,
            expires_delta=timedelta(minutes=15),
            issuer=settings.JWT_ISSUER,
            audience=settings.JWT_AUDIENCE,
            algorithm=settings.JWT_ALGORITHM,
        )

        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(token=token, db=session)

        assert exc_info.value.status_code == 401


@pytest.mark.asyncio
async def test_get_current_user_with_expired_session_raises_401():
    async with async_session() as session:
        await session.execute(text("DELETE FROM refresh_tokens"))
        await session.execute(text("DELETE FROM users"))
        await session.execute(text("DELETE FROM roles"))
        await session.commit()

        role = Role(name="user", description="Default user role")
        session.add(role)
        await session.commit()
        await session.refresh(role)

        user = User(
            username="expireduser",
            email="expired@example.com",
            hashed_password=hash_password("Password123!"),
            role=role,
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)

        refresh_token = RefreshToken(
            user_id=user.id,
            token_hash=hash_token("expired"),
            expires_at=datetime.now(timezone.utc) - timedelta(hours=1),
            revoked=False,
        )
        session.add(refresh_token)
        await session.commit()
        await session.refresh(refresh_token)

        token = create_access_token(
            data={"sub": str(user.id), "role": "user", "sid": refresh_token.id},
            secret=settings.JWT_SECRET,
            expires_delta=timedelta(minutes=15),
            issuer=settings.JWT_ISSUER,
            audience=settings.JWT_AUDIENCE,
            algorithm=settings.JWT_ALGORITHM,
        )

        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(token=token, db=session)

        assert exc_info.value.status_code == 401


@pytest.mark.asyncio
async def test_require_role_allows_correct_role():
    dependency = require_role("admin")
    current_user = SimpleNamespace(role=SimpleNamespace(name="admin"))

    result = await dependency(current_user=current_user)
    assert result is None


@pytest.mark.asyncio
async def test_require_role_rejects_incorrect_role():
    dependency = require_role("admin")
    current_user = SimpleNamespace(role=SimpleNamespace(name="user"))

    with pytest.raises(HTTPException) as exc_info:
        await dependency(current_user=current_user)

    assert exc_info.value.status_code == 403
