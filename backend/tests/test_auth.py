import asyncio
import hashlib
import pytest
from datetime import datetime, timedelta, timezone
from httpx import AsyncClient

from sqlalchemy import select

from app.core.db import async_session
from app.core.security import create_access_token, hash_password
from app.core.config import settings
from app.main import app
from app.models.refresh_token import RefreshToken
from app.models.role import Role
from app.models.user import User

pytestmark = pytest.mark.asyncio



def register_payload(username="testuser", email="test@example.com", password="Password123!"):
    return {
        "username": username,
        "email": email,
        "password": password,
        "password_confirm": password,
    }


def login_payload(username="testuser", password="Password123!"):
    return {"username": username, "password": password}


def csrf_header(client):
    token = client.cookies.get("csrf_token")
    return {"X-CSRF-Token": token} if token else {}


def assert_validation_error(response, message):
    assert response.status_code == 400
    assert response.json().get("detail") == message


def assert_unprocessable(response):
    assert response.status_code == 422
    assert isinstance(response.json().get("detail"), list)


async def create_admin_user(username="adminuser", email="admin@example.com", password="Admin123!"):
    async def _create():
        async with async_session() as session:
            role_stmt = select(Role).where(Role.name == "admin")
            role_result = await session.execute(role_stmt)
            admin_role = role_result.scalar_one_or_none()
            if admin_role is None:
                admin_role = Role(name="admin", description="Administrator role")
                session.add(admin_role)
                await session.commit()
                await session.refresh(admin_role)

            user = User(
                username=username,
                email=email,
                hashed_password=hash_password(password),
                role_id=admin_role.id,
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
            )
            session.add(user)
            await session.commit()
            await session.refresh(user)
            return user

    return await _create()


async def test_register_login_refresh_logout_flow(client):
    register_response = await client.post("/auth/register", json=register_payload())
    assert register_response.status_code == 200
    assert register_response.json()["username"] == "testuser"
    assert register_response.json()["email"] == "test@example.com"

    login_response = await client.post("/auth/login", json=login_payload())
    assert login_response.status_code == 200
    assert "access_token" in login_response.json()
    assert client.cookies.get("csrf_token") is not None
    assert client.cookies.get("refresh_token") is not None

    access_token = login_response.json()["access_token"]
    me_response = await client.get(
        "/auth/me",
        headers={"Authorization": f"Bearer {access_token}"},
    )
    assert me_response.status_code == 200
    assert me_response.json()["username"] == "testuser"

    refresh_response = await client.post(
        "/auth/refresh",
        headers=csrf_header(client),
    )
    assert refresh_response.status_code == 200
    assert "access_token" in refresh_response.json()
    assert refresh_response.json()["access_token"] != access_token

    logout_response = await client.post(
        "/auth/logout",
        headers=csrf_header(client),
    )
    assert logout_response.status_code == 200
    assert client.cookies.get("refresh_token") in (None, "")

    refresh_after_logout = await client.post(
        "/auth/refresh",
        headers=csrf_header(client),
    )
    assert refresh_after_logout.status_code in (401, 403)


async def test_refresh_rotates_and_revokes_old_refresh_token(client):
    await client.post("/auth/register", json=register_payload())
    await client.post("/auth/login", json=login_payload())
    old_refresh_token = client.cookies.get("refresh_token")
    assert old_refresh_token is not None

    refresh_response = await client.post("/auth/refresh", headers=csrf_header(client))
    assert refresh_response.status_code == 200
    new_refresh_token = client.cookies.get("refresh_token")
    assert new_refresh_token is not None
    assert new_refresh_token != old_refresh_token

    client.cookies.set("refresh_token", old_refresh_token, path="/auth")
    stale_refresh_response = await client.post("/auth/refresh", headers=csrf_header(client))
    assert stale_refresh_response.status_code == 401


async def test_refresh_without_refresh_cookie_returns_401(client):
    await client.post("/auth/register", json=register_payload())
    await client.post("/auth/login", json=login_payload())
    csrf_token = client.cookies.get("csrf_token")
    client.cookies.clear()
    client.cookies.set("csrf_token", csrf_token, path="/")

    response = await client.post("/auth/refresh", headers=csrf_header(client))
    assert response.status_code == 401


async def test_refresh_with_expired_cookie_returns_401(client):
    await client.post("/auth/register", json=register_payload())
    await client.post("/auth/login", json=login_payload())
    raw_refresh = client.cookies.get("refresh_token")
    assert raw_refresh is not None
    token_hash = hashlib.sha256(raw_refresh.encode()).hexdigest()

    async def expire_token():
        async with async_session() as session:
            stmt = select(RefreshToken).where(RefreshToken.token_hash == token_hash)
            result = await session.execute(stmt)
            token = result.scalar_one_or_none()
            assert token is not None
            token.expires_at = datetime.now(timezone.utc)
            await session.commit()

    await expire_token()

    response = await client.post("/auth/refresh", headers=csrf_header(client))
    assert response.status_code == 401


async def test_invalid_bearer_token_returns_401_for_protected_endpoints(client):
    response = await client.get(
        "/auth/me",
        headers={"Authorization": "Bearer invalid.token.value"},
    )
    assert response.status_code == 401

    response = await client.get(
        "/admin/users",
        headers={"Authorization": "Bearer invalid.token.value"},
    )
    assert response.status_code == 401


async def test_login_does_not_return_refresh_token_in_body(client):
    await client.post("/auth/register", json=register_payload())
    login_response = await client.post("/auth/login", json=login_payload())
    assert login_response.status_code == 200
    assert "refresh_token" not in login_response.json()


async def test_refresh_requires_csrf_cookie_when_refresh_cookie_present(client):
    await client.post("/auth/register", json=register_payload())
    await client.post("/auth/login", json=login_payload())
    refresh_token = client.cookies.get("refresh_token")
    assert refresh_token is not None

    client.cookies.delete("csrf_token", path="/")
    response = await client.post("/auth/refresh", headers={"X-CSRF-Token": ""})
    assert response.status_code == 403
    assert response.json().get("detail") == "Invalid CSRF token"


async def test_registration_invalid_email_and_required_fields(client):
    invalid_email = await client.post(
        "/auth/register",
        json=register_payload(email="not-an-email"),
    )
    assert_unprocessable(invalid_email)

    missing_field = await client.post(
        "/auth/register",
        json={"username": "partial", "password": "Password123!", "password_confirm": "Password123!"},
    )
    assert_unprocessable(missing_field)


async def test_admin_route_unauthenticated_returns_401(client):
    response = await client.get("/admin/users")
    assert response.status_code == 401


async def test_logout_requires_csrf_token(client):
    await client.post("/auth/register", json=register_payload())
    await client.post("/auth/login", json=login_payload())

    response = await client.post("/auth/logout")
    assert response.status_code == 403
    assert response.json().get("detail") == "Invalid CSRF token"


async def test_logout_without_refresh_cookie_still_succeeds(client):
    await client.post("/auth/register", json=register_payload())
    await client.post("/auth/login", json=login_payload())
    csrf_token = client.cookies.get("csrf_token")
    client.cookies.clear()
    client.cookies.set("csrf_token", csrf_token, path="/")

    response = await client.post("/auth/logout", headers=csrf_header(client))
    assert response.status_code == 200
    assert client.cookies.get("refresh_token") in (None, "")


async def test_delete_session_by_id_removes_session_from_list(client):
    await client.post("/auth/register", json=register_payload())
    login_response = await client.post("/auth/login", json=login_payload())
    access_token = login_response.json()["access_token"]

    sessions_response = await client.get(
        "/auth/sessions",
        headers={"Authorization": f"Bearer {access_token}"},
    )
    assert sessions_response.status_code == 200
    current_session = next((session for session in sessions_response.json() if session.get("current")), None)
    assert current_session is not None
    session_id = current_session["id"]

    delete_response = await client.delete(
        f"/auth/sessions/{session_id}",
        headers={
            **csrf_header(client),
            "Authorization": f"Bearer {access_token}",
        },
    )
    assert delete_response.status_code == 204

    verify_response = await client.get(
        "/auth/sessions",
        headers={"Authorization": f"Bearer {access_token}"},
    )
    assert verify_response.status_code == 401


async def test_user_cannot_revoke_another_users_session(client):
    await client.post("/auth/register", json=register_payload(username="user1", email="user1@example.com"))
    login1 = await client.post("/auth/login", json=login_payload(username="user1", password="Password123!"))
    token1 = login1.json()["access_token"]
    sessions1 = await client.get(
        "/auth/sessions",
        headers={"Authorization": f"Bearer {token1}"},
    )
    assert sessions1.status_code == 200
    session_id = sessions1.json()[0]["id"]

    await client.post("/auth/register", json=register_payload(username="user2", email="user2@example.com"))
    login2 = await client.post("/auth/login", json=login_payload(username="user2", password="Password123!"))
    token2 = login2.json()["access_token"]

    revoke_response = await client.delete(
        f"/auth/sessions/{session_id}",
        headers={"Authorization": f"Bearer {token2}", **csrf_header(client)},
    )
    assert revoke_response.status_code == 404

    sessions2 = await client.get(
        "/auth/sessions",
        headers={"Authorization": f"Bearer {token2}"},
    )
    assert sessions2.status_code == 200
    assert len(sessions2.json()) == 1


async def test_session_list_is_invalid_after_logout(client):
    await client.post("/auth/register", json=register_payload())
    login_response = await client.post("/auth/login", json=login_payload())
    access_token = login_response.json()["access_token"]

    logout_response = await client.post("/auth/logout", headers=csrf_header(client))
    assert logout_response.status_code == 200

    sessions_response = await client.get(
        "/auth/sessions",
        headers={"Authorization": f"Bearer {access_token}"},
    )
    assert sessions_response.status_code == 401


async def test_tampered_access_token_with_wrong_sid_is_rejected(client):
    register1 = await client.post("/auth/register", json=register_payload(username="user1", email="user1@example.com"))
    assert register1.status_code == 200
    user1_id = register1.json()["id"]

    await client.post("/auth/register", json=register_payload(username="user2", email="user2@example.com"))
    login2 = await client.post("/auth/login", json=login_payload(username="user2", password="Password123!"))
    token2 = login2.json()["access_token"]

    sessions2 = await client.get(
        "/auth/sessions",
        headers={"Authorization": f"Bearer {token2}"},
    )
    assert sessions2.status_code == 200
    other_session_id = sessions2.json()[0]["id"]

    tampered_token = create_access_token(
        data={"sub": str(user1_id), "role": "user", "sid": other_session_id},
        secret=settings.JWT_SECRET,
        expires_delta=timedelta(minutes=15),
        issuer=settings.JWT_ISSUER,
        audience=settings.JWT_AUDIENCE,
        algorithm=settings.JWT_ALGORITHM,
    )

    response = await client.get(
        "/auth/me",
        headers={"Authorization": f"Bearer {tampered_token}"},
    )
    assert response.status_code == 401


async def test_registration_rejects_weak_password(client):
    payload = register_payload(password="weakpass", email="weak@example.com")
    payload["password_confirm"] = payload["password"]
    response = await client.post("/auth/register", json=payload)
    assert response.status_code == 400
    assert "Password must contain" in response.json().get("detail", "")


async def test_registration_email_uniqueness_is_case_insensitive(client):
    first = await client.post("/auth/register", json=register_payload(email="Case@Example.com"))
    assert first.status_code == 200

    second = await client.post("/auth/register", json=register_payload(username="another", email="case@example.com"))
    assert_validation_error(second, "Email already registered")


async def test_admin_route_restricts_non_admin_users(client):
    await client.post("/auth/register", json=register_payload())
    login_response = await client.post("/auth/login", json=login_payload())
    access_token = login_response.json()["access_token"]

    response = await client.get(
        "/admin/users",
        headers={"Authorization": f"Bearer {access_token}"},
    )
    assert response.status_code == 403


async def test_admin_route_allows_admin_users(client):
    await create_admin_user()
    login_response = await client.post("/auth/login", json=login_payload(username="adminuser", password="Admin123!"))
    access_token = login_response.json()["access_token"]

    response = await client.get(
        "/admin/users",
        headers={"Authorization": f"Bearer {access_token}"},
    )
    assert response.status_code == 200
    users = response.json()
    assert isinstance(users, list)
    assert any(user["username"] == "adminuser" for user in users)


async def test_register_duplicate_username_and_email(client):
    first_response = await client.post("/auth/register", json=register_payload())
    assert first_response.status_code == 200

    username_response = await client.post(
        "/auth/register",
        json=register_payload(email="unique@example.com"),
    )
    assert_validation_error(username_response, "Username already registered")

    email_response = await client.post(
        "/auth/register",
        json=register_payload(username="unique_user"),
    )
    assert_validation_error(email_response, "Email already registered")


async def test_login_invalid_credentials(client):
    response = await client.post("/auth/login", json=login_payload(username="missing", password="badpass"))
    assert response.status_code == 401
    assert response.json().get("detail") == "Invalid credentials"


async def test_register_password_mismatch(client):
    payload = register_payload()
    payload["password_confirm"] = "Different123!"
    response = await client.post("/auth/register", json=payload)
    assert response.status_code == 400
    assert response.json().get("detail") == "Passwords do not match"


async def test_refresh_requires_csrf_token(client):
    await client.post("/auth/register", json=register_payload())
    await client.post("/auth/login", json=login_payload())
    response = await client.post("/auth/refresh")
    assert response.status_code == 403
    assert response.json().get("detail") == "Invalid CSRF token"


async def test_refresh_with_invalid_refresh_cookie_returns_401(client):
    await client.post("/auth/register", json=register_payload())
    await client.post("/auth/login", json=login_payload())
    csrf_token = client.cookies.get("csrf_token")
    client.cookies.set("refresh_token", "invalidtoken", path="/auth")
    response = await client.post("/auth/refresh", headers={"X-CSRF-Token": csrf_token})
    assert response.status_code == 401


async def test_revoke_all_sessions_invalidates_access_token(client):
    await client.post("/auth/register", json=register_payload())
    login1 = await client.post("/auth/login", json=login_payload())
    access_token1 = login1.json()["access_token"]
    await client.post("/auth/refresh", headers=csrf_header(client))
    login2 = await client.post("/auth/login", json=login_payload())
    access_token2 = login2.json()["access_token"]

    revoke_response = await client.delete(
        "/auth/sessions",
        headers={
            **csrf_header(client),
            "Authorization": f"Bearer {access_token2}",
        },
    )
    assert revoke_response.status_code == 204

    # Old token is now invalid because its refresh session was revoked.
    me_response = await client.get(
        "/auth/me",
        headers={"Authorization": f"Bearer {access_token1}"},
    )
    assert me_response.status_code == 401


async def test_get_current_user_with_token_without_sid_returns_200(client):
    register_response = await client.post("/auth/register", json=register_payload())
    user_id = register_response.json()["id"]
    token = create_access_token(
        data={"sub": str(user_id), "role": "user"},
        secret=settings.JWT_SECRET,
        expires_delta=timedelta(minutes=15),
        issuer=settings.JWT_ISSUER,
        audience=settings.JWT_AUDIENCE,
        algorithm=settings.JWT_ALGORITHM,
    )
    response = await client.get(
        "/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200


async def test_get_current_user_with_invalid_sid_returns_401(client):
    register_response = await client.post("/auth/register", json=register_payload())
    user_id = register_response.json()["id"]
    payload = create_access_token(
        data={"sub": str(user_id), "role": "user", "sid": 999999},
        secret=settings.JWT_SECRET,
        expires_delta=timedelta(minutes=15),
        issuer=settings.JWT_ISSUER,
        audience=settings.JWT_AUDIENCE,
        algorithm=settings.JWT_ALGORITHM,
    )
    response = await client.get(
        "/auth/me",
        headers={"Authorization": f"Bearer {payload}"},
    )
    assert response.status_code == 401


async def test_health_endpoint_returns_200(client):
    response = await client.get("/health")
    assert response.status_code == 200


async def test_revoke_current_session_invalidates_access_token(client):
    await client.post("/auth/register", json=register_payload())
    login_response = await client.post("/auth/login", json=login_payload())
    access_token = login_response.json()["access_token"]

    revoke_response = await client.delete(
        "/auth/sessions/current",
        headers={
            **csrf_header(client),
            "Authorization": f"Bearer {access_token}",
        },
    )
    assert revoke_response.status_code == 204

    me_response = await client.get(
        "/auth/me",
        headers={"Authorization": f"Bearer {access_token}"},
    )
    assert me_response.status_code == 401


async def test_revoke_current_session_without_active_session_returns_400(client):
    register_response = await client.post("/auth/register", json=register_payload())
    user_id = register_response.json()["id"]
    token = create_access_token(
        data={"sub": str(user_id), "role": "user"},
        secret=settings.JWT_SECRET,
        expires_delta=timedelta(minutes=15),
        issuer=settings.JWT_ISSUER,
        audience=settings.JWT_AUDIENCE,
        algorithm=settings.JWT_ALGORITHM,
    )

    client.cookies.set("csrf_token", "test-csrf", path="/")
    response = await client.delete(
        "/auth/sessions/current",
        headers={
            "Authorization": f"Bearer {token}",
            "X-CSRF-Token": "test-csrf",
        },
    )

    assert response.status_code == 400
    assert response.json().get("detail") == "No active session to revoke"


async def test_sessions_endpoint_returns_current_session_flag(client):
    await client.post("/auth/register", json=register_payload())
    login_response = await client.post("/auth/login", json=login_payload())
    access_token = login_response.json()["access_token"]

    sessions_response = await client.get(
        "/auth/sessions",
        headers={"Authorization": f"Bearer {access_token}"},
    )
    assert sessions_response.status_code == 200
    sessions = sessions_response.json()
    assert isinstance(sessions, list)
    assert len(sessions) == 1
    assert sessions[0]["current"] is True
