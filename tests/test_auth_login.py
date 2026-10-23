"""УП12. Вход, токен и текущий пользователь (критерии AC-02.x, AC-03.x)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import jwt

from app.core.security import create_access_token
from app.models import UserRole
from tests.helpers import TEST_SECRET, auth_header, create_user, login, register


def _token(client, email="user1@college.edu"):
    register(client, email)
    return login(client, email).json()["access_token"]


def test_valid_login_returns_200_and_token(client):
    register(client, "user1@college.edu")
    response = login(client, "user1@college.edu")
    assert response.status_code == 200
    body = response.json()
    assert body["token_type"] == "bearer"
    assert body["expires_in"] == 30 * 60
    assert isinstance(body["access_token"], str) and body["access_token"].count(".") == 2


def test_token_contains_user_id_role_and_expiry(client):
    user_id = register(client, "user1@college.edu").json()["id"]
    token = login(client, "user1@college.edu").json()["access_token"]
    payload = jwt.decode(token, TEST_SECRET, algorithms=["HS256"])
    assert payload["sub"] == str(user_id)
    assert payload["role"] == "student"
    exp = datetime.fromtimestamp(payload["exp"], UTC)
    assert timedelta(minutes=29) < exp - datetime.now(UTC) <= timedelta(minutes=30, seconds=5)


def test_wrong_password_returns_401(client):
    register(client, "user1@college.edu")
    response = login(client, "user1@college.edu", "Wrong123!")
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "unauthorized"
    assert "access_token" not in response.text


def test_unknown_email_returns_same_401(client):
    register(client, "user1@college.edu")
    wrong_password = login(client, "user1@college.edu", "Wrong123!").json()
    unknown_email = login(client, "nobody@college.edu").json()
    assert wrong_password == unknown_email  # не раскрываем, существует ли email


def test_inactive_user_cannot_login(client, app_session):
    create_user(app_session, "blocked@college.edu", is_active=False)
    response = login(client, "blocked@college.edu")
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "user_inactive"
    assert "access_token" not in response.text


def test_users_me_without_token_returns_401(client):
    response = client.get("/users/me")
    assert response.status_code == 401
    assert response.headers["www-authenticate"] == "Bearer"
    assert response.json()["error"]["code"] == "unauthorized"


def test_users_me_with_token_returns_profile_without_hash(client):
    token = _token(client)
    response = client.get("/users/me", headers=auth_header(token))
    assert response.status_code == 200
    body = response.json()
    assert body["email"] == "user1@college.edu"
    assert body["role"] == "student"
    assert "password_hash" not in body


def test_users_me_with_garbage_token_returns_401(client):
    response = client.get("/users/me", headers=auth_header("not.a.jwt"))
    assert response.status_code == 401


def test_users_me_with_expired_token_returns_401(client):
    user_id = register(client, "user1@college.edu").json()["id"]
    expired = create_access_token(user_id=user_id, role="student", secret_key=TEST_SECRET,
                                  expires_minutes=5, now=datetime.now(UTC) - timedelta(hours=1))
    response = client.get("/users/me", headers=auth_header(expired))
    assert response.status_code == 401
    assert "истёк" in response.json()["error"]["message"]


def test_token_signed_with_other_key_is_rejected(client):
    user_id = register(client, "user1@college.edu").json()["id"]
    forged = create_access_token(user_id=user_id, role="admin", secret_key="x" * 48, expires_minutes=5)
    assert client.get("/users/me", headers=auth_header(forged)).status_code == 401


def test_deactivated_user_token_stops_working(client, app_session):
    token = _token(client)
    from app.models import User

    user = app_session.query(User).filter_by(email="user1@college.edu").one()
    user.is_active = False
    app_session.commit()
    response = client.get("/users/me", headers=auth_header(token))
    assert response.status_code == 403


def test_operator_role_is_in_token(client, app_session):
    create_user(app_session, "op@college.edu", role=UserRole.OPERATOR)
    token = login(client, "op@college.edu").json()["access_token"]
    assert jwt.decode(token, TEST_SECRET, algorithms=["HS256"])["role"] == "operator"
    assert client.get("/users/me", headers=auth_header(token)).json()["role"] == "operator"
