from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import Select, and_, or_, select

from app.models import Ticket, TicketStatus
from app.repositories.base import BaseRepository


@dataclass(frozen=True)
class TicketFilter:
    """Фильтры списка заявок (все поля необязательны)."""

    status: TicketStatus | None = None
    priority: int | None = None
    category_id: int | None = None
    assignee_id: int | None = None
    author_id: int | None = None
    # Видимость для оператора: свои + свободные новые заявки.
    visible_to_operator_id: int | None = None


class TicketRepository(BaseRepository[Ticket]):
    model = Ticket

    def _apply_filter(self, stmt: Select, flt: TicketFilter) -> Select:
        if flt.status is not None:
            stmt = stmt.where(Ticket.status == flt.status)
        if flt.priority is not None:
            stmt = stmt.where(Ticket.priority == flt.priority)
        if flt.category_id is not None:
            stmt = stmt.where(Ticket.category_id == flt.category_id)
        if flt.assignee_id is not None:
            stmt = stmt.where(Ticket.assignee_id == flt.assignee_id)
        if flt.author_id is not None:
            stmt = stmt.where(Ticket.author_id == flt.author_id)
        if flt.visible_to_operator_id is not None:
            stmt = stmt.where(
                or_(
                    Ticket.assignee_id == flt.visible_to_operator_id,
                    and_(Ticket.assignee_id.is_(None), Ticket.status == TicketStatus.NEW),
                )
            )
        return stmt

    def list_filtered(self, flt: TicketFilter, *, limit: int = 20, offset: int = 0) -> list[Ticket]:
        stmt = self._apply_filter(select(Ticket), flt).order_by(Ticket.id).limit(limit).offset(offset)
        return list(self.session.scalars(stmt))
