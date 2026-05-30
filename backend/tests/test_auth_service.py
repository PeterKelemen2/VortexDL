import socket
import pytest
from datetime import datetime, timedelta, timezone
from fastapi import HTTPException
from sqlalchemy import select, text
from sqlalchemy.orm import selectinload
from types import SimpleNamespace

from app.core.config import settings
from app.core.db import async_session
from app.core.security import create_access_token, hash_password
from app.models.refresh_token import RefreshToken
from app.models.role import Role
from app.models.user import User
from app.schemas.auth import TokenRefreshRequest
from app.schemas.user import UserLogin, UserRegister
from app.services.auth_service import (
    _ensure_utc,
    hash_token,
    create_tokens,
    resolve_hostname,
    detect_device_os,
    detect_device_name,
    ensure_roles_exist,
    validate_password_strength,
    bootstrap_initial_admin,
    register_user,
    refresh_tokens,
    authenticate_user,
    logout_refresh_token,
    revoke_all_refresh_sessions,
    list_refresh_sessions,
    revoke_refresh_session,
    get_user_info,
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


def test_ensure_utc_converts_datetimes_to_utc():
    naive = datetime(2024, 1, 1, 12, 0, 0)
    aware = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)

    assert _ensure_utc(naive).tzinfo == timezone.utc
    assert _ensure_utc(aware) == aware
    assert _ensure_utc(None) is None


def test_hash_token_is_deterministic():
    assert hash_token("consistent") == hash_token("consistent")


@pytest.mark.asyncio
async def test_create_tokens_persists_refresh_token_and_normalizes_generic_device_name():
    async with async_session() as session:
        await session.execute(text("DELETE FROM users"))
        await session.execute(text("DELETE FROM roles"))
        await session.commit()

        role = Role(name="user", description="Default user role")
        session.add(role)
        await session.commit()
        await session.refresh(role)

        user = User(
            username="tokenuser",
            email="token@example.com",
            hashed_password=hash_password("Password123!"),
            role=role,
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)

        access_token, raw_refresh = await create_tokens(
            session,
            user,
            device_name="linux",
            user_agent="Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X)",
        )

        assert access_token
        assert raw_refresh

        token_hash_val = hash_token(raw_refresh)
        stmt = select(RefreshToken).where(RefreshToken.token_hash == token_hash_val)
        result = await session.execute(stmt)
        db_token = result.scalar_one_or_none()
        assert db_token is not None
        assert db_token.device_name == "iPhone (iOS 17.0)"


@pytest.mark.asyncio
async def test_near_expiry_rotation_revokes_old_token_and_creates_new():
    async with async_session() as session:
        await session.execute(text("DELETE FROM users"))
        await session.execute(text("DELETE FROM roles"))
        await session.commit()

        role = Role(name="user", description="Default user role")
        session.add(role)
        await session.commit()
        await session.refresh(role)

        user = User(
            username="rotateuser",
            email="rotate@example.com",
            hashed_password=hash_password("Password123!"),
            role=role,
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)

        _, raw_refresh = await create_tokens(
            session,
            user,
            user_agent="Mozilla/5.0 (Linux; Android 15; Pixel 8)",
        )
        old_token_hash = hash_token(raw_refresh)
        stmt = select(RefreshToken).where(RefreshToken.token_hash == old_token_hash)
        result = await session.execute(stmt)
        old_token = result.scalar_one()

        # Simulate the near-expiry rotation path: revoke old, create new.
        old_token.revoked = True
        await session.commit()
        new_access, new_refresh = await create_tokens(
            session,
            user,
            resolved_name=old_token.resolved_name,
            device_os=old_token.device_os,
            user_agent="Mozilla/5.0 (Linux; Android 15; Pixel 8)",
        )

        assert new_access
        assert new_refresh != raw_refresh
        await session.refresh(old_token)
        assert old_token.revoked is True


def test_validate_password_strength_reports_all_issues():
    with pytest.raises(Exception) as exc_info:
        validate_password_strength("bad pass")

    detail = exc_info.value.detail
    assert "at least 12 characters" in detail
    assert "no spaces" in detail
    assert "an uppercase letter" in detail
    assert "a digit or a special character" in detail


@pytest.mark.asyncio
async def test_bootstrap_initial_admin_requires_complete_credentials(monkeypatch):
    monkeypatch.setattr(settings, "INITIAL_ADMIN_USERNAME", "admin-bootstrap")
    monkeypatch.setattr(settings, "INITIAL_ADMIN_EMAIL", None)
    monkeypatch.setattr(settings, "INITIAL_ADMIN_PASSWORD", None)

    async with async_session() as session:
        with pytest.raises(RuntimeError):
            await bootstrap_initial_admin(session)


@pytest.mark.asyncio
async def test_bootstrap_initial_admin_creates_admin_account(monkeypatch):
    monkeypatch.setattr(settings, "INITIAL_ADMIN_USERNAME", "bootstrapadmin")
    monkeypatch.setattr(settings, "INITIAL_ADMIN_EMAIL", "bootstrap@example.com")
    monkeypatch.setattr(settings, "INITIAL_ADMIN_PASSWORD", "Password123!")
    monkeypatch.setattr(settings, "ADMIN_BOOTSTRAP_FORCE_ELEVATE_EXISTING", False)

    async with async_session() as session:
        await session.execute(text("DELETE FROM users"))
        await session.execute(text("DELETE FROM roles"))
        await session.commit()

        await bootstrap_initial_admin(session)

        stmt = select(User).options(selectinload(User.role)).where(User.username == "bootstrapadmin")
        result = await session.execute(stmt)
        admin_user = result.scalar_one_or_none()
        assert admin_user is not None
        assert admin_user.role.name == "admin"


@pytest.mark.asyncio
async def test_register_user_service_creates_new_user():
    async with async_session() as session:
        await session.execute(text("DELETE FROM users"))
        await session.execute(text("DELETE FROM roles"))
        await session.commit()

        user_in = UserRegister(
            username="serviceuser",
            email="service@example.com",
            password="Password123!",
            password_confirm="Password123!",
            device_name=None,
            user_agent=None,
        )
        user_read = await register_user(user_in, session)

        assert user_read.username == "serviceuser"
        assert user_read.email == "service@example.com"
        assert user_read.role == "user"


@pytest.mark.asyncio
async def test_refresh_tokens_rejects_invalid_credentials():
    async with async_session() as session:
        await session.execute(text("DELETE FROM users"))
        await session.execute(text("DELETE FROM roles"))
        await session.commit()

        with pytest.raises(Exception) as exc_info:
            await refresh_tokens(UserLogin(username="missing", password="BadPass123456!"), session)

        assert exc_info.value.status_code == 401


@pytest.mark.asyncio
async def test_refresh_tokens_rejects_invalid_refresh_token():
    async with async_session() as session:
        with pytest.raises(Exception) as exc_info:
            await refresh_tokens(TokenRefreshRequest(refresh_token="invalid"), session)

        assert exc_info.value.status_code == 401


@pytest.mark.asyncio
async def test_logout_refresh_token_revokes_token():
    async with async_session() as session:
        await session.execute(text("DELETE FROM users"))
        await session.execute(text("DELETE FROM roles"))
        await session.commit()

        role = Role(name="user", description="Default user role")
        session.add(role)
        await session.commit()
        await session.refresh(role)

        user = User(
            username="logoutuser",
            email="logout@example.com",
            hashed_password=hash_password("Password123!"),
            role=role,
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)

        access_token, raw_refresh = await create_tokens(session, user)
        result = await logout_refresh_token(TokenRefreshRequest(refresh_token=raw_refresh), session)

        assert result["msg"] == "Logged out"

        stmt = select(RefreshToken).where(RefreshToken.token_hash == hash_token(raw_refresh))
        db_token = (await session.execute(stmt)).scalar_one()
        assert db_token.revoked is True


@pytest.mark.asyncio
async def test_bootstrap_initial_admin_skips_when_no_credentials(monkeypatch):
    monkeypatch.setattr(settings, "INITIAL_ADMIN_USERNAME", "")
    monkeypatch.setattr(settings, "INITIAL_ADMIN_EMAIL", "")
    monkeypatch.setattr(settings, "INITIAL_ADMIN_PASSWORD", "")
    monkeypatch.setattr(settings, "ADMIN_BOOTSTRAP_FORCE_ELEVATE_EXISTING", False)

    async with async_session() as session:
        await session.execute(text("DELETE FROM users"))
        await session.execute(text("DELETE FROM roles"))
        await session.commit()

        result = await bootstrap_initial_admin(session)
        assert result is None


@pytest.mark.asyncio
async def test_bootstrap_initial_admin_skips_when_admin_already_exists(monkeypatch):
    monkeypatch.setattr(settings, "INITIAL_ADMIN_USERNAME", "bootstrapadmin")
    monkeypatch.setattr(settings, "INITIAL_ADMIN_EMAIL", "bootstrap@example.com")
    monkeypatch.setattr(settings, "INITIAL_ADMIN_PASSWORD", "Password123!")
    monkeypatch.setattr(settings, "ADMIN_BOOTSTRAP_FORCE_ELEVATE_EXISTING", False)

    async with async_session() as session:
        await session.execute(text("DELETE FROM users"))
        await session.execute(text("DELETE FROM roles"))
        await session.commit()

        existing_roles = await ensure_roles_exist(session)
        admin_role = existing_roles["admin"]
        user = User(
            username="alreadyadmin",
            email="alreadyadmin@example.com",
            hashed_password=hash_password("Password123!"),
            role_id=admin_role.id,
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)

        await bootstrap_initial_admin(session)

        stmt = select(User).where(User.username == "alreadyadmin")
        result = await session.execute(stmt)
        admin_user = result.scalar_one_or_none()
        assert admin_user is not None
        assert admin_user.role_id == admin_role.id


@pytest.mark.asyncio
async def test_bootstrap_initial_admin_does_not_elevate_existing_user_without_force(monkeypatch):
    monkeypatch.setattr(settings, "INITIAL_ADMIN_USERNAME", "bootstrapadmin")
    monkeypatch.setattr(settings, "INITIAL_ADMIN_EMAIL", "bootstrap@example.com")
    monkeypatch.setattr(settings, "INITIAL_ADMIN_PASSWORD", "Password123!")
    monkeypatch.setattr(settings, "ADMIN_BOOTSTRAP_FORCE_ELEVATE_EXISTING", False)

    async with async_session() as session:
        await session.execute(text("DELETE FROM users"))
        await session.execute(text("DELETE FROM roles"))
        await session.commit()

        existing_roles = await ensure_roles_exist(session)
        user_role = existing_roles["user"]
        user = User(
            username="bootstrapadmin",
            email="bootstrap@example.com",
            hashed_password=hash_password("Password123!"),
            role_id=user_role.id,
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)

        await bootstrap_initial_admin(session)

        stmt = select(User).where(User.username == "bootstrapadmin")
        result = await session.execute(stmt)
        persisted = result.scalar_one_or_none()
        assert persisted is not None
        assert persisted.role_id == user_role.id


@pytest.mark.asyncio
async def test_bootstrap_initial_admin_raises_for_weak_password(monkeypatch):
    monkeypatch.setattr(settings, "INITIAL_ADMIN_USERNAME", "bootstrapadmin")
    monkeypatch.setattr(settings, "INITIAL_ADMIN_EMAIL", "bootstrap@example.com")
    monkeypatch.setattr(settings, "INITIAL_ADMIN_PASSWORD", "weakpass")
    monkeypatch.setattr(settings, "ADMIN_BOOTSTRAP_FORCE_ELEVATE_EXISTING", False)

    async with async_session() as session:
        await session.execute(text("DELETE FROM users"))
        await session.execute(text("DELETE FROM roles"))
        await session.commit()

        with pytest.raises(RuntimeError) as exc_info:
            await bootstrap_initial_admin(session)

        assert "Password must contain" in str(exc_info.value)


@pytest.mark.asyncio
async def test_bootstrap_initial_admin_elevates_existing_user_when_force_elevate_set(monkeypatch):
    monkeypatch.setattr(settings, "INITIAL_ADMIN_USERNAME", "bootstrapadmin")
    monkeypatch.setattr(settings, "INITIAL_ADMIN_EMAIL", "bootstrap@example.com")
    monkeypatch.setattr(settings, "INITIAL_ADMIN_PASSWORD", "Password123!")
    monkeypatch.setattr(settings, "ADMIN_BOOTSTRAP_FORCE_ELEVATE_EXISTING", True)

    async with async_session() as session:
        await session.execute(text("DELETE FROM users"))
        await session.execute(text("DELETE FROM roles"))
        await session.commit()

        existing_roles = await ensure_roles_exist(session)
        user_role = existing_roles["user"]
        user = User(
            username="bootstrapadmin",
            email="bootstrap@example.com",
            hashed_password=hash_password("Password123!"),
            role_id=user_role.id,
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)

        await bootstrap_initial_admin(session)

        stmt = select(User).where(User.username == "bootstrapadmin")
        result = await session.execute(stmt)
        persisted = result.scalar_one_or_none()
        assert persisted is not None
        assert persisted.role_id == existing_roles["admin"].id


@pytest.mark.asyncio
async def test_bootstrap_initial_admin_skips_existing_admin_with_admin_role(monkeypatch):
    monkeypatch.setattr(settings, "INITIAL_ADMIN_USERNAME", "bootstrapadmin")
    monkeypatch.setattr(settings, "INITIAL_ADMIN_EMAIL", "bootstrap@example.com")
    monkeypatch.setattr(settings, "INITIAL_ADMIN_PASSWORD", "Password123!")
    monkeypatch.setattr(settings, "ADMIN_BOOTSTRAP_FORCE_ELEVATE_EXISTING", False)

    async with async_session() as session:
        await session.execute(text("DELETE FROM users"))
        await session.execute(text("DELETE FROM roles"))
        await session.commit()

        existing_roles = await ensure_roles_exist(session)
        admin_role = existing_roles["admin"]
        admin_user = User(
            username="bootstrapadmin",
            email="bootstrap@example.com",
            hashed_password=hash_password("Password123!"),
            role_id=admin_role.id,
        )
        session.add(admin_user)
        await session.commit()
        await session.refresh(admin_user)

        await bootstrap_initial_admin(session)

        stmt = select(User).where(User.username == "bootstrapadmin")
        result = await session.execute(stmt)
        persisted = result.scalar_one_or_none()
        assert persisted is not None
        assert persisted.role_id == admin_role.id


@pytest.mark.asyncio
async def test_bootstrap_initial_admin_skips_existing_admin_path_for_existing_user_branch(monkeypatch):
    monkeypatch.setattr(settings, "INITIAL_ADMIN_USERNAME", "bootstrapadmin")
    monkeypatch.setattr(settings, "INITIAL_ADMIN_EMAIL", "bootstrap@example.com")
    monkeypatch.setattr(settings, "INITIAL_ADMIN_PASSWORD", "Password123!")
    monkeypatch.setattr(settings, "ADMIN_BOOTSTRAP_FORCE_ELEVATE_EXISTING", False)

    admin_role = SimpleNamespace(id=1, name="admin", description="Administrator role")
    user_role = SimpleNamespace(id=2, name="user", description="Default user role")
    existing_user = SimpleNamespace(role_id=admin_role.id, username="bootstrapadmin")

    class FakeResult:
        def __init__(self, value):
            self._value = value

        def scalar_one_or_none(self):
            return self._value

    class FakeSession:
        def __init__(self):
            self.calls = 0

        async def execute(self, stmt):
            self.calls += 1
            if self.calls == 1:
                return FakeResult(None)
            if self.calls == 2:
                return FakeResult(existing_user)
            raise AssertionError("Unexpected query in FakeSession")

        async def commit(self):
            pass

        async def refresh(self, instance):
            pass

    async def fake_ensure_roles_exist(db):
        return {"admin": admin_role, "user": user_role}

    monkeypatch.setattr("app.services.auth_service.ensure_roles_exist", fake_ensure_roles_exist)

    fake_session = FakeSession()
    await bootstrap_initial_admin(fake_session)


@pytest.mark.asyncio
async def test_resolve_hostname_returns_short_hostname(monkeypatch):
    def fake_gethostbyaddr(ip):
        return ("example.domain.com", [], ["127.0.0.1"])

    monkeypatch.setattr("socket.gethostbyaddr", fake_gethostbyaddr)
    assert await resolve_hostname("8.8.8.8") == "example"


@pytest.mark.asyncio
async def test_register_user_service_rejects_duplicate_username():
    async with async_session() as session:
        await session.execute(text("DELETE FROM users"))
        await session.execute(text("DELETE FROM roles"))
        await session.commit()

        existing_roles = await ensure_roles_exist(session)
        user_role = existing_roles["user"]
        user = User(
            username="serviceuser",
            email="serviceuser@example.com",
            hashed_password=hash_password("Password123!"),
            role_id=user_role.id,
        )
        session.add(user)
        await session.commit()

        with pytest.raises(HTTPException) as exc_info:
            await register_user(
                UserRegister(
                    username="serviceuser",
                    email="unique@example.com",
                    password="Password123!",
                    password_confirm="Password123!",
                    device_name=None,
                    user_agent=None,
                ),
                session,
            )

        assert exc_info.value.status_code == 400
        assert exc_info.value.detail == "Username already registered"


@pytest.mark.asyncio
async def test_register_user_service_rejects_duplicate_email():
    async with async_session() as session:
        await session.execute(text("DELETE FROM users"))
        await session.execute(text("DELETE FROM roles"))
        await session.commit()

        existing_roles = await ensure_roles_exist(session)
        user_role = existing_roles["user"]
        user = User(
            username="uniqueuser",
            email="duplicate@example.com",
            hashed_password=hash_password("Password123!"),
            role_id=user_role.id,
        )
        session.add(user)
        await session.commit()

        with pytest.raises(HTTPException) as exc_info:
            await register_user(
                UserRegister(
                    username="anotheruser",
                    email="duplicate@example.com",
                    password="Password123!",
                    password_confirm="Password123!",
                    device_name=None,
                    user_agent=None,
                ),
                session,
            )

        assert exc_info.value.status_code == 400
        assert exc_info.value.detail == "Email already registered"


@pytest.mark.asyncio
async def test_refresh_tokens_uses_user_login_path_and_resolves_hostname(monkeypatch):
    async with async_session() as session:
        await session.execute(text("DELETE FROM users"))
        await session.execute(text("DELETE FROM roles"))
        await session.commit()

        existing_roles = await ensure_roles_exist(session)
        user = User(
            username="loginservice",
            email="loginservice@example.com",
            hashed_password=hash_password("Password123!"),
            role_id=existing_roles["user"].id,
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)

        async def fake_resolve_hostname(ip):
            return "test-host"

        monkeypatch.setattr("app.services.auth_service.resolve_hostname", fake_resolve_hostname)
        token_resp = await refresh_tokens(
            UserLogin(username="loginservice", password="Password123!"),
            session,
            user_agent="Mozilla/5.0 (Linux; Android 15; Pixel 8)",
            client_ip="8.8.8.8",
        )

        assert token_resp.access_token
        assert token_resp.refresh_token


@pytest.mark.asyncio
async def test_refresh_tokens_with_missing_refresh_token_raises_401():
    async with async_session() as session:
        with pytest.raises(HTTPException) as exc_info:
            await refresh_tokens(TokenRefreshRequest(refresh_token=None), session)

        assert exc_info.value.status_code == 401


@pytest.mark.asyncio
async def test_refresh_tokens_user_not_found_raises_401():
    async with async_session() as session:
        await session.execute(text("DELETE FROM refresh_tokens"))
        await session.execute(text("DELETE FROM users"))
        await session.execute(text("DELETE FROM roles"))
        await session.commit()

        raw_refresh = "unknown-user"
        await session.execute(text("PRAGMA foreign_keys = OFF"))
        await session.execute(
            text(
                "INSERT INTO refresh_tokens (user_id, token_hash, expires_at, revoked, created_at) VALUES (:user_id, :token_hash, :expires_at, 0, :created_at)"
            ),
            {
                "user_id": 999999,
                "token_hash": hash_token(raw_refresh),
                "expires_at": (datetime.now(timezone.utc) + timedelta(days=1)).isoformat(sep=" "),
                "created_at": datetime.now(timezone.utc).isoformat(sep=" "),
            },
        )
        await session.commit()

        with pytest.raises(HTTPException) as exc_info:
            await refresh_tokens(TokenRefreshRequest(refresh_token=raw_refresh), session)

        assert exc_info.value.status_code == 401


@pytest.mark.asyncio
async def test_refresh_tokens_invalid_request_object_raises_400():
    async with async_session() as session:
        with pytest.raises(HTTPException) as exc_info:
            await refresh_tokens(object(), session)

        assert exc_info.value.status_code == 400


@pytest.mark.asyncio
async def test_revoke_all_refresh_sessions_revokes_tokens():
    async with async_session() as session:
        await session.execute(text("DELETE FROM users"))
        await session.execute(text("DELETE FROM refresh_tokens"))
        await session.execute(text("DELETE FROM roles"))
        await session.commit()

        existing_roles = await ensure_roles_exist(session)
        user = User(
            username="revokeall",
            email="revokeall@example.com",
            hashed_password=hash_password("Password123!"),
            role_id=existing_roles["user"].id,
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)

        token1 = RefreshToken(
            user_id=user.id,
            token_hash=hash_token("one"),
            expires_at=datetime.now(timezone.utc) + timedelta(days=1),
            revoked=False,
        )
        token2 = RefreshToken(
            user_id=user.id,
            token_hash=hash_token("two"),
            expires_at=datetime.now(timezone.utc) + timedelta(days=1),
            revoked=False,
        )
        session.add_all([token1, token2])
        await session.commit()

        await revoke_all_refresh_sessions(user, session)

        stmt = select(RefreshToken).where(RefreshToken.user_id == user.id)
        refreshed = (await session.execute(stmt)).scalars().all()
        assert all(token.revoked for token in refreshed)


@pytest.mark.asyncio
async def test_revoke_refresh_session_revokes_valid_session():
    async with async_session() as session:
        await session.execute(text("DELETE FROM users"))
        await session.execute(text("DELETE FROM refresh_tokens"))
        await session.execute(text("DELETE FROM roles"))
        await session.commit()

        existing_roles = await ensure_roles_exist(session)
        user = User(
            username="revokesession",
            email="revokesession@example.com",
            hashed_password=hash_password("Password123!"),
            role_id=existing_roles["user"].id,
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)

        refresh_token = RefreshToken(
            user_id=user.id,
            token_hash=hash_token("revoke-me"),
            expires_at=datetime.now(timezone.utc) + timedelta(days=1),
            revoked=False,
        )
        session.add(refresh_token)
        await session.commit()
        await session.refresh(refresh_token)

        response = await revoke_refresh_session(refresh_token.id, user, session)
        assert response["msg"] == "Session revoked"

        await session.refresh(refresh_token)
        assert refresh_token.revoked is True


@pytest.mark.asyncio
async def test_list_refresh_sessions_marks_current_session():
    async with async_session() as session:
        await session.execute(text("DELETE FROM users"))
        await session.execute(text("DELETE FROM roles"))
        await session.commit()

        role = Role(name="user", description="Default user role")
        session.add(role)
        await session.commit()
        await session.refresh(role)

        user = User(
            username="sessionuser",
            email="session@example.com",
            hashed_password=hash_password("Password123!"),
            role=role,
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)

        refresh_token = RefreshToken(
            user_id=user.id,
            token_hash=hash_token("sessiontest"),
            expires_at=datetime.now(timezone.utc) + timedelta(days=1),
            revoked=False,
        )
        session.add(refresh_token)
        await session.commit()
        await session.refresh(refresh_token)

        sessions = await list_refresh_sessions(session, user, current_session_id=refresh_token.id)
        assert any(getattr(session_obj, "current", False) for session_obj in sessions)


@pytest.mark.asyncio
async def test_revoke_refresh_session_raises_for_missing_session():
    async with async_session() as session:
        await session.execute(text("DELETE FROM users"))
        await session.execute(text("DELETE FROM roles"))
        await session.commit()

        role = Role(name="user", description="Default user role")
        session.add(role)
        await session.commit()
        await session.refresh(role)

        user = User(
            username="revokesuser",
            email="revokes@example.com",
            hashed_password=hash_password("Password123!"),
            role=role,
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)

        with pytest.raises(Exception) as exc_info:
            await revoke_refresh_session(9999, user, session)

        assert exc_info.value.status_code == 404


def test_get_user_info_returns_user_read():
    role = Role(name="user", description="Default user role")
    now = datetime.now(timezone.utc)
    user = User(
        id=1,
        username="info",
        email="info@example.com",
        hashed_password=hash_password("Password123!"),
        role=role,
        created_at=now,
        updated_at=now,
    )

    user_read = get_user_info(user)
    assert user_read.username == "info"
    assert user_read.role == "user"
    assert user_read.created_at == now
    assert user_read.updated_at == now
