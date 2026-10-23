"""Настройки приложения из переменных окружения.

Единственное место в проекте, где читаются переменные окружения. Остальной код
получает настройки через ``get_settings()``.

Правила:
* ``APP_ENV`` — ``dev`` (по умолчанию), ``test`` или ``prod``;
* в ``dev`` для ``DATABASE_URL`` и ``SECRET_KEY`` есть безопасные для учёбы значения
  по умолчанию, поэтому сервис запускается одной командой без настройки;
* в ``test`` и ``prod`` переменные ``DATABASE_URL`` и ``SECRET_KEY`` обязательны:
  если какой-то нет, выбрасывается ``ConfigError`` с понятным сообщением.

Если в корне проекта есть файл ``.env``, его строки ``KEY=VALUE`` подхватываются
(уже заданные переменные окружения имеют приоритет).
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]

ALLOWED_ENVS = ("dev", "test", "prod")
REQUIRED_IN_STRICT_ENVS = ("DATABASE_URL", "SECRET_KEY")

DEV_DEFAULTS = {
    "DATABASE_URL": f"sqlite:///{(PROJECT_ROOT / 'college_tickets.db').as_posix()}",
    "SECRET_KEY": "dev-only-insecure-secret-key-change-me-in-production-0123456789",
}


class ConfigError(RuntimeError):
    """Ошибка конфигурации: не задана или неверна переменная окружения."""


@dataclass(frozen=True)
class Settings:
    app_env: str
    database_url: str
    secret_key: str
    access_token_expire_minutes: int = 60
    jwt_algorithm: str = "HS256"
    host: str = "127.0.0.1"
    port: int = 8000
    first_admin_email: str | None = None
    first_admin_password: str | None = None
    app_name: str = "College Ticket Service"
    app_version: str = "0.2.0"


def _load_dotenv(path: Path) -> dict[str, str]:
    """Простой разбор файла .env без сторонних библиотек."""
    values: dict[str, str] = {}
    if not path.is_file():
        return values
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip().strip('"').strip("'")
    return values


def _int_var(env: dict[str, str], name: str, default: int, minimum: int = 1) -> int:
    raw = env.get(name)
    if raw is None or raw == "":
        return default
    try:
        value = int(raw)
    except ValueError as exc:
        raise ConfigError(
            f"Переменная окружения {name} должна быть целым числом, получено: {raw!r}"
        ) from exc
    if value < minimum:
        raise ConfigError(f"Переменная окружения {name} должна быть >= {minimum}, получено: {value}")
    return value


def load_settings(environ: dict[str, str] | None = None, dotenv_path: Path | None = None) -> Settings:
    """Собрать настройки из окружения (по умолчанию ``os.environ`` + ``.env``)."""
    if environ is None:
        env = _load_dotenv(dotenv_path or PROJECT_ROOT / ".env")
        env.update(os.environ)
    else:
        env = dict(environ)

    app_env = (env.get("APP_ENV") or "dev").strip().lower()
    if app_env not in ALLOWED_ENVS:
        raise ConfigError(
            f"Переменная окружения APP_ENV имеет недопустимое значение {app_env!r}. "
            f"Допустимо: {', '.join(ALLOWED_ENVS)}."
        )

    if app_env in ("test", "prod"):
        missing = [name for name in REQUIRED_IN_STRICT_ENVS if not env.get(name)]
        if missing:
            names = ", ".join(missing)
            raise ConfigError(
                f"Не задана обязательная переменная окружения: {names} (APP_ENV={app_env}). "
                f"Задайте её перед запуском, например: {missing[0]}=... "
                f"(образец — в файле .env.example)."
            )
        database_url = env["DATABASE_URL"]
        secret_key = env["SECRET_KEY"]
    else:
        database_url = env.get("DATABASE_URL") or DEV_DEFAULTS["DATABASE_URL"]
        secret_key = env.get("SECRET_KEY") or DEV_DEFAULTS["SECRET_KEY"]

    if app_env == "prod" and len(secret_key) < 32:
        raise ConfigError("SECRET_KEY в prod должен быть не короче 32 символов.")

    return Settings(
        app_env=app_env,
        database_url=database_url,
        secret_key=secret_key,
        access_token_expire_minutes=_int_var(env, "ACCESS_TOKEN_EXPIRE_MINUTES", 60),
        host=env.get("HOST") or "127.0.0.1",
        port=_int_var(env, "PORT", 8000),
        first_admin_email=env.get("FIRST_ADMIN_EMAIL") or None,
        first_admin_password=env.get("FIRST_ADMIN_PASSWORD") or None,
    )


@lru_cache
def get_settings() -> Settings:
    """Настройки процесса (кэшируются; в тестах сбрасываются через ``get_settings.cache_clear()``)."""
    return load_settings()
