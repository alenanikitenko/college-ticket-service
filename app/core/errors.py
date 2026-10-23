"""Доменные исключения.

Сервисы выбрасывают эти исключения, а обработчик в ``app.main`` превращает их
в HTTP-ответ единого формата ``{"error": {"code", "message", "details"}}``.
Модуль не импортирует FastAPI, поэтому сервисы остаются независимыми от HTTP.
"""

from __future__ import annotations

from typing import Any


class AppError(Exception):
    status_code: int = 400
    code: str = "bad_request"
    message: str = "Некорректный запрос"

    def __init__(self, message: str | None = None, *, details: Any = None) -> None:
        self.message = message or self.message
        self.details = details
        super().__init__(self.message)


class NotFoundError(AppError):
    status_code = 404
    code = "not_found"
    message = "Ресурс не найден"


class ConflictError(AppError):
    status_code = 409
    code = "conflict"
    message = "Конфликт с текущим состоянием ресурса"


class AuthenticationError(AppError):
    status_code = 401
    code = "unauthorized"
    message = "Требуется аутентификация"


class PermissionDeniedError(AppError):
    status_code = 403
    code = "forbidden"
    message = "Недостаточно прав для операции"


class InactiveUserError(AppError):
    status_code = 403
    code = "user_inactive"
    message = "Учётная запись отключена"


class InvalidTransitionError(AppError):
    status_code = 409
    code = "invalid_transition"
    message = "Недопустимый переход статуса"


class ServiceUnavailableError(AppError):
    status_code = 503
    code = "service_unavailable"
    message = "Сервис временно недоступен"
