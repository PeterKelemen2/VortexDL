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
