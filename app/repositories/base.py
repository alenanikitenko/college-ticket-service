"""Базовый репозиторий.

Правила слоя:
* работает только с переданной ``Session`` и ORM-моделями;
* НЕ импортирует FastAPI и НЕ вызывает ``commit``/``rollback`` — транзакцией
  управляет сервис; репозиторий делает только ``flush``, чтобы получить id.
"""

from __future__ import annotations

from typing import Generic, TypeVar

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.database import Base

ModelT = TypeVar("ModelT", bound=Base)


class BaseRepository(Generic[ModelT]):
    model: type[ModelT]

    def __init__(self, session: Session) -> None:
        self.session = session

    def add(self, obj: ModelT) -> ModelT:
        self.session.add(obj)
        self.session.flush()
        return obj

    def get(self, obj_id: int) -> ModelT | None:
        return self.session.get(self.model, obj_id)

    def list(self, *, limit: int = 100, offset: int = 0) -> list[ModelT]:
        stmt = select(self.model).order_by(self.model.id).limit(limit).offset(offset)
        return list(self.session.scalars(stmt))

    def count(self) -> int:
        return self.session.scalar(select(func.count()).select_from(self.model)) or 0

    def delete(self, obj: ModelT) -> None:
        self.session.delete(obj)
        self.session.flush()
