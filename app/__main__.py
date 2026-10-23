"""Запуск сервиса одной командой: ``python -m app``.

1. читает настройки из окружения / .env;
2. применяет миграции Alembic до последней версии (``upgrade head``);
3. запускает uvicorn на HOST:PORT (по умолчанию http://127.0.0.1:8000).
"""

from __future__ import annotations

import sys

import uvicorn

from app.core.config import ConfigError, get_settings
from app.db_migrate import upgrade_head


def main() -> int:
    try:
        settings = get_settings()
    except ConfigError as exc:
        print(f"Ошибка конфигурации: {exc}", file=sys.stderr)
        return 2
    upgrade_head(settings.database_url)
    print(f"Swagger UI: http://{settings.host}:{settings.port}/docs")
    uvicorn.run("app.main:app", host=settings.host, port=settings.port)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
