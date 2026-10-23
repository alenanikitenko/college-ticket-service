"""Общие типы колонок."""

from __future__ import annotations

from datetime import UTC, datetime
from enum import Enum

from sqlalchemy import DateTime
from sqlalchemy import Enum as SAEnum
from sqlalchemy.types import TypeDecorator


def utcnow() -> datetime:
    return datetime.now(UTC)


class UTCDateTime(TypeDecorator):
    """Дата-время в UTC.

    SQLite не хранит часовой пояс, поэтому значение записывается как UTC без зоны,
    а при чтении к нему снова добавляется ``UTC``. В API всегда уходит время с зоной.
    """

    impl = DateTime
    cache_ok = True

    def process_bind_param(self, value: datetime | None, dialect):
        if value is None:
            return None
        if value.tzinfo is None:
            value = value.replace(tzinfo=UTC)
        return value.astimezone(UTC).replace(tzinfo=None)

    def process_result_value(self, value: datetime | None, dialect):
        if value is None:
            return None
        return value.replace(tzinfo=UTC)


def str_enum(enum_cls: type[Enum], name: str, length: int = 20) -> SAEnum:
    """Enum, который хранится как VARCHAR + CHECK (переносимо между SQLite и PostgreSQL)."""
    return SAEnum(
        enum_cls,
        name=name,
        native_enum=False,
        create_constraint=True,
        length=length,
        validate_strings=True,
        values_callable=lambda e: [member.value for member in e],
    )
