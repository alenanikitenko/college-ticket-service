"""Схемы пользователя. Ни одна выходная схема не содержит ``password_hash``."""

from __future__ import annotations

from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from app.models.enums import UserRole

FullName = Annotated[str, Field(min_length=2, max_length=100, examples=["Иван Петров"])]
Password = Annotated[str, Field(min_length=8, max_length=128, examples=["Secret123!"])]


def _normalize_email(value: str) -> str:
    return value.strip().lower()


class UserRegister(BaseModel):
    """Тело регистрации. Лишние поля (например ``role``) запрещены: роль задаёт сервер."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    email: EmailStr = Field(examples=["user1@college.edu"])
    full_name: FullName
    password: Password

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        return _normalize_email(value)


class LoginRequest(BaseModel):
    email: EmailStr = Field(examples=["user1@college.edu"])
    password: str = Field(min_length=1, max_length=128, examples=["Secret123!"])

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        return _normalize_email(value)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int = Field(description="Срок действия токена в секундах")


class UserRead(BaseModel):
    """Публичное представление пользователя (без пароля и хэша)."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    email: EmailStr
    full_name: str
    role: UserRole
    is_active: bool
    created_at: datetime


class UserAdminUpdate(BaseModel):
    """Изменение роли/активности пользователя администратором."""

    model_config = ConfigDict(extra="forbid")

    role: UserRole | None = None
    is_active: bool | None = None
