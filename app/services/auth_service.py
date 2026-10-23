"""Регистрация, вход и определение текущего пользователя."""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.core.errors import AuthenticationError, ConflictError, InactiveUserError
from app.core.security import (
    TokenError,
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)
from app.models import User, UserRole
from app.repositories import UserRepository
from app.schemas.user import UserRegister
from app.services.base import transaction

INVALID_CREDENTIALS = "Неверный email или пароль"

# Хэш-«пустышка»: проверяем пароль даже для несуществующего email,
# чтобы время ответа не выдавало, зарегистрирован ли адрес.
_DUMMY_HASH = hash_password("dummy-password-for-timing")


@dataclass(frozen=True)
class IssuedToken:
    access_token: str
    expires_in: int
    token_type: str = "bearer"


class AuthService:
    def __init__(self, session: Session, settings: Settings) -> None:
        self.session = session
        self.settings = settings
        self.users = UserRepository(session)

    # --- регистрация ---------------------------------------------------------
    def register(self, data: UserRegister, *, role: UserRole = UserRole.STUDENT) -> User:
        """Создать пользователя. Повторный email → ``ConflictError`` (HTTP 409)."""
        email = data.email.strip().lower()
        if self.users.get_by_email(email) is not None:
            raise ConflictError("Пользователь с таким email уже существует")
        try:
            with transaction(self.session):
                user = self.users.add(
                    User(
                        email=email,
                        full_name=data.full_name,
                        role=role,
                        password_hash=hash_password(data.password),
                        is_active=True,
                    )
                )
        except IntegrityError as exc:  # гонка двух одновременных регистраций
            raise ConflictError("Пользователь с таким email уже существует") from exc
        return user

    # --- вход ----------------------------------------------------------------
    def authenticate(self, email: str, password: str) -> User:
        user = self.users.get_by_email(email)
        if user is None:
            verify_password(password, _DUMMY_HASH)
            raise AuthenticationError(INVALID_CREDENTIALS)
        if not verify_password(password, user.password_hash):
            raise AuthenticationError(INVALID_CREDENTIALS)
        if not user.is_active:
            raise InactiveUserError("Учётная запись отключена, вход запрещён")
        return user

    def issue_token(self, user: User) -> IssuedToken:
        minutes = self.settings.access_token_expire_minutes
        token = create_access_token(
            user_id=user.id,
            role=user.role.value,
            secret_key=self.settings.secret_key,
            expires_minutes=minutes,
            algorithm=self.settings.jwt_algorithm,
        )
        return IssuedToken(access_token=token, expires_in=minutes * 60)

    def login(self, email: str, password: str) -> IssuedToken:
        return self.issue_token(self.authenticate(email, password))

    # --- текущий пользователь -----------------------------------------------
    def user_from_token(self, token: str) -> User:
        try:
            payload = decode_access_token(
                token, secret_key=self.settings.secret_key, algorithm=self.settings.jwt_algorithm
            )
        except TokenError as exc:
            raise AuthenticationError(str(exc)) from exc
        user = self.users.get(payload["user_id"])
        if user is None:
            raise AuthenticationError("Пользователь из токена не найден")
        if not user.is_active:
            raise InactiveUserError("Учётная запись отключена")
        return user

    # --- первый администратор ------------------------------------------------
    def ensure_admin(self, email: str, password: str, full_name: str = "Администратор") -> User:
        """Создать администратора, если пользователя с таким email ещё нет (идемпотентно)."""
        existing = self.users.get_by_email(email)
        if existing is not None:
            return existing
        data = UserRegister(email=email, full_name=full_name, password=password)
        return self.register(data, role=UserRole.ADMIN)
