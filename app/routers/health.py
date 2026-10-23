from __future__ import annotations

from fastapi import APIRouter
from sqlalchemy import text

from app.core.errors import ServiceUnavailableError
from app.routers.deps import DbSession
from app.schemas.common import ErrorResponse, HealthResponse

router = APIRouter(tags=["service"])


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Проверка работоспособности",
    responses={503: {"model": ErrorResponse, "description": "БД недоступна"}},
)
def health(db: DbSession) -> HealthResponse:
    try:
        db.execute(text("SELECT 1"))
    except Exception as exc:  # noqa: BLE001 — любая ошибка БД = сервис недоступен
        raise ServiceUnavailableError("База данных недоступна") from exc
    return HealthResponse(status="ok")
