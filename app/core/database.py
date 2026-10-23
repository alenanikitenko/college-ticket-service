"""Подключение к БД: декларативная база, движок и фабрика сессий SQLAlchemy."""

from __future__ import annotations

from collections.abc import Iterator

from sqlalchemy import Engine, MetaData, create_engine, event
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

# Единые имена ограничений: Alembic генерирует предсказуемые миграции,
# а SQLite (batch-режим) может удалять ограничения по имени.
NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    """Базовый класс всех ORM-моделей."""

    metadata = MetaData(naming_convention=NAMING_CONVENTION)


def _enable_sqlite_foreign_keys(dbapi_connection, _connection_record) -> None:
    # SQLite по умолчанию НЕ проверяет внешние ключи — включаем для каждого соединения.
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


def make_engine(database_url: str, echo: bool = False) -> Engine:
    """Создать движок; для SQLite включает внешние ключи и работу из нескольких потоков."""
    is_sqlite = database_url.startswith("sqlite")
    connect_args = {"check_same_thread": False} if is_sqlite else {}
    engine = create_engine(database_url, echo=echo, connect_args=connect_args)
    if is_sqlite:
        event.listen(engine, "connect", _enable_sqlite_foreign_keys)
    return engine


def make_session_factory(engine: Engine) -> sessionmaker[Session]:
    """Фабрика сессий. ``expire_on_commit=False`` — объекты доступны после commit."""
    return sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def session_scope(factory: sessionmaker[Session]) -> Iterator[Session]:
    """Генератор сессии для зависимостей: гарантированно закрывает сессию."""
    session = factory()
    try:
        yield session
    finally:
        session.close()
