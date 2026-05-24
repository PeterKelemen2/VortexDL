import socket
import pytest
from sqlalchemy import select, text

from app.core.db import async_session
from app.core.security import hash_password
from app.models.role import Role
from app.models.user import User
from app.services.auth_service import (
    resolve_hostname,
    detect_device_os,
    detect_device_name,
    ensure_roles_exist,
    validate_password_strength,
    authenticate_user,
)


def test_detect_device_os_various_user_agents():
    assert detect_device_os("Mozilla/5.0 (Linux; Android 12; Pixel 6)") == "android"
    assert detect_device_os("Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X)") == "ios"
    assert detect_device_os("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)") == "macos"
    assert detect_device_os("Mozilla/5.0 (Windows NT 10.0; Win64; x64)") == "windows"
    assert detect_device_os("Mozilla/5.0 (X11; Linux x86_64)") == "linux"
    assert detect_device_os(None) == "other"


def test_detect_device_name_parses_common_user_agents():
    assert detect_device_name("Mozilla/5.0 (Linux; Android 15; Pixel 8)") == "Android 15 Pixel 8"
    assert detect_device_name("Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X)") == "iPhone (iOS 17.0)"
    assert detect_device_name("Mozilla/5.0 (Windows NT 10.0; Win64; x64)") == "Windows 10/11"
    assert detect_device_name("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)") == "macOS 10.15.7"
    assert detect_device_name("Mozilla/5.0 (X11; Linux x86_64)") == "Linux PC"
    assert detect_device_name(None) is None


@pytest.mark.asyncio
async def test_resolve_hostname_returns_none_for_loopback():
    assert await resolve_hostname("127.0.0.1") is None
    assert await resolve_hostname("::1") is None


@pytest.mark.asyncio
async def test_resolve_hostname_handles_lookup_failure(monkeypatch):
    def fake_gethostbyaddr(ip):
        raise socket.herror

    monkeypatch.setattr(socket, "gethostbyaddr", fake_gethostbyaddr)
    assert await resolve_hostname("8.8.8.8") is None


@pytest.mark.asyncio
async def test_ensure_roles_exist_creates_missing_roles():
    async with async_session() as session:
        await session.execute(text("DELETE FROM users"))
        await session.execute(text("DELETE FROM roles"))
        await session.commit()
        roles = await ensure_roles_exist(session)
        assert "admin" in roles
        assert "user" in roles
        assert roles["admin"].id is not None
        assert roles["user"].id is not None


def test_validate_password_strength_rejects_weak_password():
    with pytest.raises(Exception):
        validate_password_strength("weak")


@pytest.mark.asyncio
async def test_authenticate_user_returns_user_with_valid_password():
    async with async_session() as session:
        await session.execute(text("DELETE FROM users"))
        await session.execute(text("DELETE FROM roles"))
        await session.commit()
        role = Role(name="user", description="Default user role")
        session.add(role)
        await session.commit()
        await session.refresh(role)
        user = User(
            username="authuser",
            email="auth@example.com",
            hashed_password=hash_password("Password123!"),
            role_id=role.id,
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)
        authenticated = await authenticate_user(session, "authuser", "Password123!")
        assert authenticated is not None
        assert authenticated.username == "authuser"
        failure = await authenticate_user(session, "authuser", "wrongpass")
        assert failure is None
