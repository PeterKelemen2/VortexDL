import pytest
from datetime import datetime, timedelta, timezone
from sqlalchemy import text
from starlette.requests import Request
from starlette.responses import Response

from app.core.db import async_session
from app.core.security import create_access_token, hash_password
from app.models.role import Role
from app.models.user import User
from app.models.refresh_token import RefreshToken
from app.services.auth_service import ensure_roles_exist, create_tokens, hash_token
from app.api.routes.auth import login, refresh, revoke_all_sessions, revoke_current_session, revoke_session
from app.schemas.user import UserLogin
from app.schemas.auth import TokenRefreshRequest


async def _empty_receive():
    return {"type": "http.request", "body": b"", "more_body": False}


def build_request(headers: dict[str, str] | None = None, cookies: str | None = None) -> Request:
    scope = {
        "type": "http",
        "method": "POST",
        "path": "/auth/login",
        "headers": [],
        "client": ("127.0.0.1", 12345),
        "scheme": "http",
        "server": ("testserver", 80),
        "root_path": "",
        "query_string": b"",
    }
    header_list = []
    if headers:
        for key, value in headers.items():
            header_list.append((key.lower().encode("utf-8"), value.encode("utf-8")))
    if cookies:
        header_list.append((b"cookie", cookies.encode("utf-8")))
    scope["headers"] = header_list
    return Request(scope, _empty_receive)


@pytest.mark.asyncio
async def test_login_route_direct_sets_cookie_headers():
    async with async_session() as session:
        await session.execute(text("DELETE FROM users"))
        await session.execute(text("DELETE FROM roles"))
        await session.commit()

        roles = await ensure_roles_exist(session)
        user = User(
            username="directlogin",
            email="directlogin@example.com",
            hashed_password=hash_password("Password123!"),
            role_id=roles["user"].id,
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)

        request = build_request(headers={"user-agent": "test-agent"})
        response = Response()
        token_response = await login(
            UserLogin(username="directlogin", password="Password123!"),
            request,
            response,
            session,
        )

        assert token_response.access_token
        set_cookie = response.headers.getlist("set-cookie")
        assert any("refresh_token=" in cookie for cookie in set_cookie)
        assert any("csrf_token=" in cookie for cookie in set_cookie)


@pytest.mark.asyncio
async def test_refresh_route_direct_rotates_refresh_cookie():
    async with async_session() as session:
        await session.execute(text("DELETE FROM users"))
        await session.execute(text("DELETE FROM roles"))
        await session.commit()

        roles = await ensure_roles_exist(session)
        user = User(
            username="directrefresh",
            email="directrefresh@example.com",
            hashed_password=hash_password("Password123!"),
            role_id=roles["user"].id,
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)

        _, raw_refresh = await create_tokens(session, user)
        csrf_token = "direct-csrf-token"
        request = build_request(
            headers={"user-agent": "test-agent", "x-csrf-token": csrf_token},
            cookies=f"refresh_token={raw_refresh}; csrf_token={csrf_token}",
        )
        response = Response()

        token_response = await refresh(request, response, session)
        assert token_response.access_token
        set_cookie_headers = response.headers.getlist("set-cookie")
        assert any("refresh_token=" in cookie for cookie in set_cookie_headers)
        assert any("csrf_token=" in cookie for cookie in set_cookie_headers)


@pytest.mark.asyncio
async def test_revoke_all_sessions_route_direct_returns_none():
    async with async_session() as session:
        await session.execute(text("DELETE FROM users"))
        await session.execute(text("DELETE FROM roles"))
        await session.commit()

        roles = await ensure_roles_exist(session)
        user = User(
            username="directrevokeall",
            email="directrevokeall@example.com",
            hashed_password=hash_password("Password123!"),
            role_id=roles["user"].id,
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)

        request = build_request(headers={"x-csrf-token": "csrf-token"}, cookies="csrf_token=csrf-token")
        result = await revoke_all_sessions(request, user, session)
        assert result is None


@pytest.mark.asyncio
async def test_revoke_session_route_direct_returns_none():
    async with async_session() as session:
        await session.execute(text("DELETE FROM users"))
        await session.execute(text("DELETE FROM refresh_tokens"))
        await session.execute(text("DELETE FROM roles"))
        await session.commit()

        roles = await ensure_roles_exist(session)
        user = User(
            username="directrevokesession",
            email="directrevokesession@example.com",
            hashed_password=hash_password("Password123!"),
            role_id=roles["user"].id,
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)

        refresh_token = RefreshToken(
            user_id=user.id,
            token_hash=hash_token("direct-session"),
            expires_at=datetime.now(timezone.utc) + timedelta(days=1),
            revoked=False,
        )
        session.add(refresh_token)
        await session.commit()
        await session.refresh(refresh_token)

        request = build_request(headers={"x-csrf-token": "csrf-token"}, cookies="csrf_token=csrf-token")
        result = await revoke_session(request, refresh_token.id, user, session)
        assert result is None


@pytest.mark.asyncio
async def test_revoke_current_session_route_direct_returns_none():
    async with async_session() as session:
        await session.execute(text("DELETE FROM users"))
        await session.execute(text("DELETE FROM refresh_tokens"))
        await session.execute(text("DELETE FROM roles"))
        await session.commit()

        roles = await ensure_roles_exist(session)
        user = User(
            username="directcursession",
            email="directcursession@example.com",
            hashed_password=hash_password("Password123!"),
            role_id=roles["user"].id,
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)

        refresh_token = RefreshToken(
            user_id=user.id,
            token_hash=hash_token("direct-current"),
            expires_at=datetime.now(timezone.utc) + timedelta(days=1),
            revoked=False,
        )
        session.add(refresh_token)
        await session.commit()
        await session.refresh(refresh_token)

        user.current_session_id = refresh_token.id
        request = build_request(headers={"x-csrf-token": "csrf-token"}, cookies="csrf_token=csrf-token")
        result = await revoke_current_session(request, user, session)
        assert result is None
