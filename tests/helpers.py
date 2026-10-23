"""Помощники для тестов (не фикстуры)."""

from __future__ import annotations

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.models import Category, User, UserRole

TEST_SECRET = "test-secret-key-for-pytest-only-0123456789abcdef"
DEFAULT_PASSWORD = "Secret123!"

def register(client: TestClient, email: str = "user1@college.edu", password: str = DEFAULT_PASSWORD,
             full_name: str = "Иван Петров"):
    return client.post(
        "/auth/register", json={"email": email, "full_name": full_name, "password": password}
    )


def login(client: TestClient, email: str = "user1@college.edu", password: str = DEFAULT_PASSWORD):
    return client.post("/auth/login", json={"email": email, "password": password})


def auth_header(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def create_user(session: Session, email: str, role: UserRole = UserRole.STUDENT,
                is_active: bool = True, password: str = DEFAULT_PASSWORD) -> User:
    user = User(email=email, full_name="Тестовый Пользователь", role=role,
                password_hash=hash_password(password), is_active=is_active)
    session.add(user)
    session.commit()
    return user


def create_category(session: Session, name: str = "IT") -> Category:
    category = Category(name=name)
    session.add(category)
    session.commit()
    return category
