from __future__ import annotations

from fastapi import APIRouter, status

from app.routers.deps import AuthServiceDep
from app.schemas.common import ErrorResponse
from app.schemas.user import LoginRequest, TokenResponse, UserRead, UserRegister

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post(
    "/register",
    response_model=UserRead,
    status_code=status.HTTP_201_CREATED,
    summary="Регистрация (роль student)",
    responses={
        409: {"model": ErrorResponse, "description": "Email уже зарегистрирован"},
        422: {"model": ErrorResponse, "description": "Ошибка валидации"},
    },
)
def register(data: UserRegister, auth: AuthServiceDep) -> UserRead:
    user = auth.register(data)
    return UserRead.model_validate(user)


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Вход: выдача JWT",
    responses={
        401: {"model": ErrorResponse, "description": "Неверный email или пароль"},
        403: {"model": ErrorResponse, "description": "Пользователь неактивен"},
        422: {"model": ErrorResponse, "description": "Ошибка валидации"},
    },
)
def login(data: LoginRequest, auth: AuthServiceDep) -> TokenResponse:
    issued = auth.login(data.email, data.password)
    return TokenResponse(
        access_token=issued.access_token, token_type=issued.token_type, expires_in=issued.expires_in
    )
