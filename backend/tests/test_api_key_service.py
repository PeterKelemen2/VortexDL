"""Unit tests for the user-owned API key service."""
from datetime import datetime, timedelta, timezone

import pytest
from fastapi import HTTPException
from sqlalchemy import select, text

from app.core.db import async_session
from app.models.api_key import ApiKey
from app.models.role import Role
from app.models.user import User
from app.schemas.api_key import ApiKeyCreate
from app.services.api_key_service import (
    KEY_PREFIX,
    create_api_key,
    list_api_keys,
    resolve_api_key,
    revoke_api_key,
)

pytestmark = pytest.mark.asyncio


async def _reset(session):
    await session.execute(text("DELETE FROM api_keys"))
    await session.execute(text("DELETE FROM users"))
    await session.execute(text("DELETE FROM roles"))
    await session.commit()


async def _make_user(session, username="apiuser", email="apiuser@example.com") -> User:
    role = (
        await session.execute(select(Role).where(Role.name == "user"))
    ).scalar_one_or_none()
    if role is None:
        role = Role(name="user", description="Default user role")
        session.add(role)
        await session.commit()
        await session.refresh(role)

    user = User(
        username=username,
        email=email,
        hashed_password="irrelevant",
        role=role,
    )
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return user


async def test_create_api_key_returns_plaintext_once():
    async with async_session() as session:
        await _reset(session)
        user = await _make_user(session)

        api_key, plaintext = await create_api_key(
            ApiKeyCreate(name="ci-token"), user.id, session
        )

        assert plaintext.startswith(KEY_PREFIX)
        assert api_key.name == "ci-token"
        # The stored prefix is a short, non-secret display identifier.
        assert plaintext.startswith(api_key.prefix)
        assert api_key.key_hash != plaintext
        assert api_key.revoked is False
        assert api_key.expires_at is None


async def test_create_api_key_with_expiry_sets_future_timestamp():
    async with async_session() as session:
        await _reset(session)
        user = await _make_user(session)

        api_key, _ = await create_api_key(
            ApiKeyCreate(name="temp", expires_in_days=7), user.id, session
        )

        assert api_key.expires_at is not None
        # SQLite returns the persisted value tz-naive; normalise before diffing.
        expires_at = api_key.expires_at
        now = datetime.now(timezone.utc)
        if expires_at.tzinfo is None:
            now = now.replace(tzinfo=None)
        delta = expires_at - now
        # Allow a small window for execution time.
        assert timedelta(days=6, hours=23) < delta <= timedelta(days=7)


async def test_list_api_keys_scoped_to_owner():
    async with async_session() as session:
        await _reset(session)
        owner = await _make_user(session, "owner", "owner@example.com")
        other = await _make_user(session, "other", "other@example.com")

        await create_api_key(ApiKeyCreate(name="a"), owner.id, session)
        await create_api_key(ApiKeyCreate(name="b"), owner.id, session)
        await create_api_key(ApiKeyCreate(name="c"), other.id, session)

        owner_keys = await list_api_keys(owner.id, session)
        other_keys = await list_api_keys(other.id, session)

        assert {k.name for k in owner_keys} == {"a", "b"}
        assert {k.name for k in other_keys} == {"c"}


async def test_revoke_api_key_marks_revoked():
    async with async_session() as session:
        await _reset(session)
        user = await _make_user(session)
        api_key, _ = await create_api_key(
            ApiKeyCreate(name="to-revoke"), user.id, session
        )

        await revoke_api_key(api_key.id, user.id, session)

        refreshed = await session.get(ApiKey, api_key.id)
        assert refreshed.revoked is True


async def test_revoke_api_key_rejects_non_owner():
    async with async_session() as session:
        await _reset(session)
        owner = await _make_user(session, "owner", "owner@example.com")
        attacker = await _make_user(session, "attacker", "attacker@example.com")
        api_key, _ = await create_api_key(ApiKeyCreate(name="k"), owner.id, session)

        with pytest.raises(HTTPException) as exc:
            await revoke_api_key(api_key.id, attacker.id, session)
        assert exc.value.status_code == 404


async def test_resolve_api_key_authenticates_valid_key():
    async with async_session() as session:
        await _reset(session)
        user = await _make_user(session)
        _, plaintext = await create_api_key(ApiKeyCreate(name="k"), user.id, session)

        resolved = await resolve_api_key(plaintext, session)

        assert resolved is not None
        assert resolved.id == user.id


async def test_resolve_api_key_rejects_revoked_key():
    async with async_session() as session:
        await _reset(session)
        user = await _make_user(session)
        api_key, plaintext = await create_api_key(
            ApiKeyCreate(name="k"), user.id, session
        )
        await revoke_api_key(api_key.id, user.id, session)

        assert await resolve_api_key(plaintext, session) is None


async def test_resolve_api_key_rejects_expired_key():
    async with async_session() as session:
        await _reset(session)
        user = await _make_user(session)
        api_key, plaintext = await create_api_key(
            ApiKeyCreate(name="k", expires_in_days=1), user.id, session
        )
        # Force expiry into the past.
        api_key.expires_at = datetime.now(timezone.utc) - timedelta(seconds=1)
        await session.commit()

        assert await resolve_api_key(plaintext, session) is None


async def test_resolve_api_key_rejects_malformed_key():
    async with async_session() as session:
        await _reset(session)
        assert await resolve_api_key("not-a-valid-key", session) is None
        assert await resolve_api_key("", session) is None


async def test_resolve_api_key_updates_last_used():
    async with async_session() as session:
        await _reset(session)
        user = await _make_user(session)
        api_key, plaintext = await create_api_key(
            ApiKeyCreate(name="k"), user.id, session
        )
        assert api_key.last_used_at is None

        await resolve_api_key(plaintext, session)

        refreshed = await session.get(ApiKey, api_key.id)
        assert refreshed.last_used_at is not None
