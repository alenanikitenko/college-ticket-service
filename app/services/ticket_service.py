"""Бизнес-логика заявок (на этапе УП9 — создание заявки с записью аудита)."""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.core.errors import NotFoundError, PermissionDeniedError
from app.models import AuditAction, Ticket, TicketStatus, User, UserRole
from app.repositories import AuditEventRepository, CategoryRepository, TicketRepository
from app.schemas.ticket import TicketCreate
from app.services.base import transaction


class TicketService:
    def __init__(self, session: Session) -> None:
        self.session = session
        self.tickets = TicketRepository(session)
        self.categories = CategoryRepository(session)
        self.audit = AuditEventRepository(session)

    def create_ticket(self, author: User, data: TicketCreate) -> Ticket:
        """Создать заявку и событие аудита в ОДНОЙ транзакции.

        Если запись аудита не удалась, откатывается и сама заявка.
        """
        if author.role != UserRole.STUDENT:
            raise PermissionDeniedError("Создавать заявки может только студент")
        if self.categories.get(data.category_id) is None:
            raise NotFoundError("Категория не найдена")
        with transaction(self.session):
            ticket = self.tickets.add(
                Ticket(
                    title=data.title,
                    description=data.description,
                    priority=data.priority,
                    category_id=data.category_id,
                    author_id=author.id,
                    status=TicketStatus.NEW,
                )
            )
            self.audit.record(ticket_id=ticket.id, actor_id=author.id, action=AuditAction.TICKET_CREATED)
        return ticket
