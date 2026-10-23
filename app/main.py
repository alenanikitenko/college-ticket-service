"""Точка сборки FastAPI-приложения.

``create_app()`` создаёт экземпляр с собственными настройками и движком БД —
это позволяет тестам поднимать приложение на временной SQLite.
Модульная переменная ``app`` используется uvicorn: ``uvicorn app.main:app``.
"""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from typing import Any

from fastapi import FastAPI, Request, status
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy import inspect, text
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.config import Settings, get_settings
from app.core.database import make_engine, make_session_factory
from app.core.errors import AppError
from app.routers import auth, health, users
from app.services import AuthService

logger = logging.getLogger("college_ticket_service")

HTTP_CODE_NAMES = {
    400: "bad_request",
    401: "unauthorized",
    403: "forbidden",
    404: "not_found",
    405: "method_not_allowed",
    409: "conflict",
    422: "validation_error",
    500: "internal_error",
    503: "service_unavailable",
}


def error_payload(code: str, message: str, details: Any = None) -> dict[str, Any]:
    return {"error": {"code": code, "message": message, "details": details}}


def _auth_headers(status_code: int) -> dict[str, str] | None:
    return {"WWW-Authenticate": "Bearer"} if status_code == 401 else None


def register_exception_handlers(app: FastAPI) -> None:
    """Все ошибки приводятся к единому формату ``{"error": {...}}``."""

    @app.exception_handler(AppError)
    async def handle_app_error(_: Request, exc: AppError) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content=jsonable_encoder(error_payload(exc.code, exc.message, exc.details)),
            headers=_auth_headers(exc.status_code),
        )

    @app.exception_handler(StarletteHTTPException)
    async def handle_http_error(_: Request, exc: StarletteHTTPException) -> JSONResponse:
        code = HTTP_CODE_NAMES.get(exc.status_code, "http_error")
        message = exc.detail if isinstance(exc.detail, str) else code
        headers = dict(exc.headers or {}) | (_auth_headers(exc.status_code) or {})
        return JSONResponse(
            status_code=exc.status_code,
            content=error_payload(code, message),
            headers=headers or None,
        )

    @app.exception_handler(RequestValidationError)
    async def handle_validation_error(_: Request, exc: RequestValidationError) -> JSONResponse:
        details = [
            {
                "field": ".".join(str(part) for part in err.get("loc", ())),
                "message": err.get("msg", ""),
                "type": err.get("type", ""),
            }
            for err in exc.errors()
        ]
        return JSONResponse(
            status_code=422,
            content=error_payload("validation_error", "Ошибка валидации входных данных", details),
        )

    @app.exception_handler(Exception)
    async def handle_unexpected(_: Request, exc: Exception) -> JSONResponse:
        logger.exception("Необработанная ошибка: %s", exc)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=error_payload("internal_error", "Внутренняя ошибка сервера"),
        )


def _on_startup(app: FastAPI) -> None:
    """Обработчик запуска: проверка БД и (опционально) создание первого администратора."""
    settings: Settings = app.state.settings
    engine = app.state.engine
    with engine.connect() as conn:
        conn.execute(text("SELECT 1"))
    if settings.first_admin_email and settings.first_admin_password:
        if not inspect(engine).has_table("users"):
            logger.warning("Таблицы нет — выполните миграции (alembic upgrade head) до создания админа")
        else:
            with app.state.session_factory() as session:
                AuthService(session, settings).ensure_admin(
                    settings.first_admin_email, settings.first_admin_password
                )
    app.state.started_at = datetime.now(UTC)
    logger.info("%s запущен (APP_ENV=%s)", settings.app_name, settings.app_env)


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        _on_startup(app)
        yield
        app.state.engine.dispose()
        logger.info("%s остановлен", settings.app_name)

    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description=(
            "REST API «Сервис заявок колледжа»: студенты создают заявки, операторы их обрабатывают, "
            "администраторы управляют категориями и пользователями.\n\n"
            "Ошибки возвращаются в формате `{\"error\": {\"code\", \"message\", \"details\"}}`."
        ),
        lifespan=lifespan,
        openapi_tags=[
            {"name": "service", "description": "Служебные маршруты"},
            {"name": "auth", "description": "Регистрация и вход"},
            {"name": "users", "description": "Пользователи и профиль"},
        ],
    )
    app.state.settings = settings
    app.state.engine = make_engine(settings.database_url)
    app.state.session_factory = make_session_factory(app.state.engine)
    app.state.started_at = None

    register_exception_handlers(app)
    app.include_router(health.router)
    app.include_router(auth.router)
    app.include_router(users.router)
    return app


app = create_app()
