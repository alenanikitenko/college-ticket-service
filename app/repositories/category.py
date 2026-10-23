from __future__ import annotations

from sqlalchemy import func, select

from app.models import Category, Ticket
from app.repositories.base import BaseRepository


class CategoryRepository(BaseRepository[Category]):
    model = Category

    def get_by_name(self, name: str) -> Category | None:
        return self.session.scalar(select(Category).where(Category.name == name.strip()))

    def has_tickets(self, category_id: int) -> bool:
        stmt = select(func.count()).select_from(Ticket).where(Ticket.category_id == category_id)
        return (self.session.scalar(stmt) or 0) > 0
