"""FastAPI-зависимости: сессия БД, настройки, текущий пользователь, проверка роли."""

from __future__ import annotations

from collections.abc import Callable, Iterator
from typing import Annotated

from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.core.database import session_scope
from app.core.errors import AuthenticationError, PermissionDeniedError
from app.models import User, UserRole
from app.services import AuthService

bearer_scheme = HTTPBearer(auto_error=False, description="JWT из POST /auth/login")


def get_settings_dep(request: Request) -> Settings:
    return request.app.state.settings


def get_db(request: Request) -> Iterator[Session]:
    yield from session_scope(request.app.state.session_factory)


SettingsDep = Annotated[Settings, Depends(get_settings_dep)]
DbSession = Annotated[Session, Depends(get_db)]


def get_auth_service(db: DbSession, settings: SettingsDep) -> AuthService:
    return AuthService(db, settings)


AuthServiceDep = Annotated[AuthService, Depends(get_auth_service)]


def get_current_user(
    auth: AuthServiceDep,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
) -> User:
    """Пользователь из заголовка ``Authorization: Bearer <token>``; иначе 401."""
    if credentials is None or credentials.scheme.lower() != "bearer" or not credentials.credentials:
        raise AuthenticationError("Требуется заголовок Authorization: Bearer <token>")
    return auth.user_from_token(credentials.credentials)


CurrentUser = Annotated[User, Depends(get_current_user)]


def require_roles(*roles: UserRole) -> Callable[[User], User]:
    """Зависимость: пропускает только пользователей с одной из указанных ролей (иначе 403)."""

    def checker(user: CurrentUser) -> User:
        if user.role not in roles:
            raise PermissionDeniedError(
                f"Операция доступна ролям: {', '.join(r.value for r in roles)}"
            )
        return user

    return checker
