from __future__ import annotations

from fastapi import APIRouter

from app.routers.deps import CurrentUser
from app.schemas.common import ErrorResponse
from app.schemas.user import UserRead

router = APIRouter(prefix="/users", tags=["users"])


@router.get(
    "/me",
    response_model=UserRead,
    summary="Профиль текущего пользователя",
    responses={401: {"model": ErrorResponse, "description": "Нет токена или он недействителен"}},
)
def read_me(user: CurrentUser) -> UserRead:
    return UserRead.model_validate(user)
