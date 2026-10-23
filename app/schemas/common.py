"""Общие схемы: единый формат ошибки."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict


class ErrorBody(BaseModel):
    code: str
    message: str
    details: Any | None = None


class ErrorResponse(BaseModel):
    """Единый формат ошибки API: ``{"error": {"code", "message", "details"}}``."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {"error": {"code": "conflict", "message": "Email уже занят", "details": None}}
        }
    )

    error: ErrorBody


class HealthResponse(BaseModel):
    status: str = "ok"
