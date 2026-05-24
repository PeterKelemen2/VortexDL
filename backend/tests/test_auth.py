import asyncio
from datetime import datetime

from sqlalchemy import select

from app.core.db import async_session
from app.core.security import hash_password
from app.models.role import Role
from app.models.user import User


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


def create_admin_user(username="adminuser", email="admin@example.com", password="Admin123!"):
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
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
            )
            session.add(user)
            await session.commit()
            await session.refresh(user)
            return user

    return asyncio.run(_create())


def test_register_login_refresh_logout_flow(client):
    register_response = client.post("/auth/register", json=register_payload())
    assert register_response.status_code == 200
    assert register_response.json()["username"] == "testuser"
    assert register_response.json()["email"] == "test@example.com"

    login_response = client.post("/auth/login", json=login_payload())
    assert login_response.status_code == 200
    assert "access_token" in login_response.json()
    assert client.cookies.get("csrf_token") is not None
    assert client.cookies.get("refresh_token") is not None

    access_token = login_response.json()["access_token"]
    me_response = client.get(
        "/auth/me",
        headers={"Authorization": f"Bearer {access_token}"},
    )
    assert me_response.status_code == 200
    assert me_response.json()["username"] == "testuser"

    refresh_response = client.post(
        "/auth/refresh",
        headers=csrf_header(client),
    )
    assert refresh_response.status_code == 200
    assert "access_token" in refresh_response.json()
    assert refresh_response.json()["access_token"] != access_token

    logout_response = client.post(
        "/auth/logout",
        headers=csrf_header(client),
    )
    assert logout_response.status_code == 200
    assert client.cookies.get("refresh_token") in (None, "")

    refresh_after_logout = client.post(
        "/auth/refresh",
        headers=csrf_header(client),
    )
    assert refresh_after_logout.status_code in (401, 403)


def test_refresh_rotates_and_revokes_old_refresh_token(client):
    client.post("/auth/register", json=register_payload())
    client.post("/auth/login", json=login_payload())
    old_refresh_token = client.cookies.get("refresh_token")
    assert old_refresh_token is not None

    refresh_response = client.post("/auth/refresh", headers=csrf_header(client))
    assert refresh_response.status_code == 200
    new_refresh_token = client.cookies.get("refresh_token")
    assert new_refresh_token is not None
    assert new_refresh_token != old_refresh_token

    client.cookies.set("refresh_token", old_refresh_token, path="/auth")
    stale_refresh_response = client.post("/auth/refresh", headers=csrf_header(client))
    assert stale_refresh_response.status_code == 401


def test_admin_route_restricts_non_admin_users(client):
    client.post("/auth/register", json=register_payload())
    login_response = client.post("/auth/login", json=login_payload())
    access_token = login_response.json()["access_token"]

    response = client.get(
        "/admin/users",
        headers={"Authorization": f"Bearer {access_token}"},
    )
    assert response.status_code == 403


def test_admin_route_allows_admin_users(client):
    create_admin_user()
    login_response = client.post("/auth/login", json=login_payload(username="adminuser", password="Admin123!"))
    access_token = login_response.json()["access_token"]

    response = client.get(
        "/admin/users",
        headers={"Authorization": f"Bearer {access_token}"},
    )
    assert response.status_code == 200
    users = response.json()
    assert isinstance(users, list)
    assert any(user["username"] == "adminuser" for user in users)


def test_register_duplicate_username_and_email(client):
    first_response = client.post("/auth/register", json=register_payload())
    assert first_response.status_code == 200

    username_response = client.post(
        "/auth/register",
        json=register_payload(email="unique@example.com"),
    )
    assert_validation_error(username_response, "Username already registered")

    email_response = client.post(
        "/auth/register",
        json=register_payload(username="unique_user"),
    )
    assert_validation_error(email_response, "Email already registered")


def test_login_invalid_credentials(client):
    response = client.post("/auth/login", json=login_payload(username="missing", password="badpass"))
    assert response.status_code == 401
    assert response.json().get("detail") == "Invalid credentials"


def test_register_password_mismatch(client):
    payload = register_payload()
    payload["password_confirm"] = "Different123!"
    response = client.post("/auth/register", json=payload)
    assert response.status_code == 400
    assert response.json().get("detail") == "Passwords do not match"


def test_refresh_requires_csrf_token(client):
    client.post("/auth/register", json=register_payload())
    client.post("/auth/login", json=login_payload())
    response = client.post("/auth/refresh")
    assert response.status_code == 403
    assert response.json().get("detail") == "Invalid CSRF token"


def test_revoke_current_session_invalidates_access_token(client):
    client.post("/auth/register", json=register_payload())
    login_response = client.post("/auth/login", json=login_payload())
    access_token = login_response.json()["access_token"]

    revoke_response = client.delete(
        "/auth/sessions/current",
        headers={
            **csrf_header(client),
            "Authorization": f"Bearer {access_token}",
        },
    )
    assert revoke_response.status_code == 204

    me_response = client.get(
        "/auth/me",
        headers={"Authorization": f"Bearer {access_token}"},
    )
    assert me_response.status_code == 401


def test_sessions_endpoint_returns_current_session_flag(client):
    client.post("/auth/register", json=register_payload())
    login_response = client.post("/auth/login", json=login_payload())
    access_token = login_response.json()["access_token"]

    sessions_response = client.get(
        "/auth/sessions",
        headers={"Authorization": f"Bearer {access_token}"},
    )
    assert sessions_response.status_code == 200
    sessions = sessions_response.json()
    assert isinstance(sessions, list)
    assert len(sessions) == 1
    assert sessions[0]["current"] is True
