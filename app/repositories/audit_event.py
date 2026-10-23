from __future__ import annotations

from sqlalchemy import select

from app.models import AuditAction, AuditEvent
from app.repositories.base import BaseRepository


class AuditEventRepository(BaseRepository[AuditEvent]):
    model = AuditEvent

    def record(self, *, ticket_id: int, actor_id: int, action: AuditAction) -> AuditEvent:
        return self.add(AuditEvent(ticket_id=ticket_id, actor_id=actor_id, action=action))

    def list_for_ticket(self, ticket_id: int) -> list[AuditEvent]:
        stmt = (
            select(AuditEvent)
            .where(AuditEvent.ticket_id == ticket_id)
            .order_by(AuditEvent.created_at, AuditEvent.id)
        )
        return list(self.session.scalars(stmt))
