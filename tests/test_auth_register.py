"""УП11. Регистрация и хэширование пароля (критерии AC-01.1 – AC-01.3)."""

from __future__ import annotations

from sqlalchemy import func, select

from app.core.security import verify_password
from app.models import User, UserRole
from tests.helpers import DEFAULT_PASSWORD, register


def test_register_user1_returns_201_without_hash(client):
    response = register(client, "user1@college.edu")
    assert response.status_code == 201
    body = response.json()
    assert body["email"] == "user1@college.edu"
    assert body["full_name"] == "Иван Петров"
    assert body["role"] == "student"
    assert body["is_active"] is True
    assert isinstance(body["id"], int)
    assert "password_hash" not in body
    assert "password" not in body
    assert DEFAULT_PASSWORD not in response.text


def test_duplicate_email_returns_409_and_does_not_create_user(client, app_session):
    assert register(client, "user1@college.edu").status_code == 201
    response = register(client, "user1@college.edu", full_name="Другой Человек")
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "conflict"
    assert app_session.scalar(select(func.count()).select_from(User)) == 1


def test_duplicate_email_is_case_insensitive(client):
    assert register(client, "user1@college.edu").status_code == 201
    assert register(client, "USER1@College.edu").status_code == 409


def test_password_is_stored_only_as_strong_hash(client, app_session):
    register(client, "user1@college.edu")
    user = app_session.scalar(select(User).where(User.email == "user1@college.edu"))
    assert user.password_hash != DEFAULT_PASSWORD
    assert DEFAULT_PASSWORD not in user.password_hash
    assert user.password_hash.startswith("scrypt$")
    assert verify_password(DEFAULT_PASSWORD, user.password_hash) is True
    assert verify_password("Wrong123!", user.password_hash) is False


def test_same_password_gives_different_hashes(client, app_session):
    register(client, "a@college.edu")
    register(client, "b@college.edu")
    hashes = list(app_session.scalars(select(User.password_hash)))
    assert len(set(hashes)) == 2  # уникальная соль у каждого пользователя


def test_default_role_is_student(client, app_session):
    register(client, "user1@college.edu")
    user = app_session.scalar(select(User))
    assert user.role == UserRole.STUDENT


def test_client_cannot_choose_role(client):
    response = client.post("/auth/register", json={
        "email": "hacker@college.edu", "full_name": "Хакер", "password": DEFAULT_PASSWORD, "role": "admin",
    })
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"


def test_invalid_body_returns_unified_422(client):
    response = client.post("/auth/register", json={"email": "not-an-email", "full_name": "Я",
                                                   "password": "short"})
    assert response.status_code == 422
    error = response.json()["error"]
    assert error["code"] == "validation_error"
    fields = {d["field"] for d in error["details"]}
    assert {"body.email", "body.full_name", "body.password"} <= fields
