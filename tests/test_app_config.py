"""УП6. Каркас приложения и конфигурация."""

from __future__ import annotations

import pytest

from app.core.config import ConfigError, load_settings
from app.main import create_app


def test_health_returns_200_status_ok(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_missing_required_variable_in_test_config_gives_clear_message():
    with pytest.raises(ConfigError) as exc_info:
        load_settings({"APP_ENV": "test", "DATABASE_URL": "sqlite://"})  # нет SECRET_KEY
    message = str(exc_info.value)
    assert "SECRET_KEY" in message
    assert "APP_ENV=test" in message
    assert "Не задана обязательная переменная окружения" in message


def test_startup_handler_runs_and_openapi_is_available(settings):
    app = create_app(settings)
    assert app.state.started_at is None
    from fastapi.testclient import TestClient

    with TestClient(app) as client:  # запускает lifespan (обработчик запуска)
        assert app.state.started_at is not None
        schema = client.get("/openapi.json").json()
    assert schema["info"]["title"] == "College Ticket Service"
    assert {"/health", "/auth/register", "/auth/login", "/users/me"} <= set(schema["paths"])


# --- дополнительные проверки конфигурации ---------------------------------------

def test_missing_database_url_in_test_config_is_reported():
    with pytest.raises(ConfigError, match="DATABASE_URL"):
        load_settings({"APP_ENV": "test", "SECRET_KEY": "x" * 40})


def test_invalid_app_env_is_rejected():
    with pytest.raises(ConfigError, match="APP_ENV"):
        load_settings({"APP_ENV": "staging"})


def test_non_integer_expire_minutes_is_rejected():
    with pytest.raises(ConfigError, match="ACCESS_TOKEN_EXPIRE_MINUTES"):
        load_settings({"APP_ENV": "dev", "ACCESS_TOKEN_EXPIRE_MINUTES": "abc"})


def test_dev_config_has_defaults_and_reads_variables():
    s = load_settings({"APP_ENV": "dev", "ACCESS_TOKEN_EXPIRE_MINUTES": "15", "PORT": "9000"})
    assert s.database_url.startswith("sqlite:///")
    assert s.secret_key
    assert s.access_token_expire_minutes == 15
    assert s.port == 9000


def test_short_secret_rejected_in_prod():
    with pytest.raises(ConfigError, match="32"):
        load_settings({"APP_ENV": "prod", "DATABASE_URL": "sqlite://", "SECRET_KEY": "short"})


def test_dotenv_file_is_loaded(tmp_path, monkeypatch):
    env_file = tmp_path / ".env"
    env_file.write_text("APP_ENV=dev\nPORT=8123\n# комментарий\n", encoding="utf-8")
    for name in ("APP_ENV", "PORT"):
        monkeypatch.delenv(name, raising=False)
    s = load_settings(dotenv_path=env_file)
    assert s.port == 8123


def test_python_m_app_reports_config_error(monkeypatch, capsys):
    from app import __main__ as entry
    from app.core.config import get_settings

    monkeypatch.setenv("APP_ENV", "test")
    monkeypatch.delenv("SECRET_KEY", raising=False)
    monkeypatch.setattr("app.core.config.PROJECT_ROOT", __import__("pathlib").Path("/nonexistent"))
    get_settings.cache_clear()
    assert entry.main() == 2
    assert "SECRET_KEY" in capsys.readouterr().err


def test_unknown_route_uses_unified_error_format(client):
    response = client.get("/no-such-route")
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "not_found"


def test_health_returns_503_when_database_fails(app, client):
    from app.routers.deps import get_db

    class BrokenSession:
        def execute(self, *args, **kwargs):
            raise RuntimeError("database is locked")

    app.dependency_overrides[get_db] = lambda: BrokenSession()
    try:
        response = client.get("/health")
    finally:
        app.dependency_overrides.clear()
    assert response.status_code == 503
    assert response.json()["error"]["code"] == "service_unavailable"
