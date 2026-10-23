"""Общие фикстуры тестов.

Каждый тест получает собственную временную SQLite-базу в ``tmp_path``,
поэтому тесты независимы друг от друга и не требуют сети.
"""

from __future__ import annotations

import os

# Переменные выставляются ДО импорта приложения: модуль app.main создаёт
# экземпляр приложения при импорте, а в test-конфигурации они обязательны.
os.environ["APP_ENV"] = "test"
os.environ.setdefault("SECRET_KEY", "test-secret-key-for-pytest-only-0123456789abcdef")
os.environ.setdefault("DATABASE_URL", "sqlite://")

from collections.abc import Iterator  # noqa: E402
from pathlib import Path  # noqa: E402

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy.orm import Session  # noqa: E402

from app.core.config import Settings, get_settings, load_settings  # noqa: E402
from app.core.database import make_engine, make_session_factory  # noqa: E402
from app.main import create_app  # noqa: E402
from app.models import Base  # noqa: E402

from tests.helpers import TEST_SECRET  # noqa: E402


def make_test_settings(db_path: Path, **overrides: str) -> Settings:
    env = {
        "APP_ENV": "test",
        "DATABASE_URL": f"sqlite:///{db_path.as_posix()}",
        "SECRET_KEY": TEST_SECRET,
        "ACCESS_TOKEN_EXPIRE_MINUTES": "30",
    }
    env.update(overrides)
    return load_settings(env)


@pytest.fixture(autouse=True)
def _clear_settings_cache() -> Iterator[None]:
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.fixture
def settings(tmp_path: Path) -> Settings:
    return make_test_settings(tmp_path / "test.db")


@pytest.fixture
def engine(settings: Settings):
    eng = make_engine(settings.database_url)
    Base.metadata.create_all(eng)
    yield eng
    eng.dispose()


@pytest.fixture
def db_session(engine) -> Iterator[Session]:
    session = make_session_factory(engine)()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def app(settings: Settings):
    application = create_app(settings)
    Base.metadata.create_all(application.state.engine)
    return application


@pytest.fixture
def client(app) -> Iterator[TestClient]:
    with TestClient(app) as test_client:  # with — чтобы выполнился обработчик запуска
        yield test_client


@pytest.fixture
def app_session(app) -> Iterator[Session]:
    """Сессия к той же БД, что и у приложения, — для проверки данных напрямую."""
    session = app.state.session_factory()
    try:
        yield session
    finally:
        session.close()
