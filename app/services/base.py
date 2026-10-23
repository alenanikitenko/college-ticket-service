"""Управление транзакцией в сервисном слое.

Сервис открывает блок ``with transaction(session):`` — внутри работают
репозитории (``add``/``flush``), а в конце выполняется ровно один ``commit``.
Любое исключение внутри блока приводит к ``rollback``: в БД не остаётся
частично записанных данных.
"""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager

from sqlalchemy.orm import Session


@contextmanager
def transaction(session: Session) -> Iterator[Session]:
    try:
        yield session
        session.commit()
    except BaseException:
        session.rollback()
        raise
