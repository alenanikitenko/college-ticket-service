"""Перечисления предметной области (хранятся в БД как строки с CHECK-ограничением)."""

from __future__ import annotations

from enum import StrEnum


class UserRole(StrEnum):
    STUDENT = "student"
    OPERATOR = "operator"
    ADMIN = "admin"


class TicketStatus(StrEnum):
    NEW = "new"
    IN_PROGRESS = "in_progress"
    RESOLVED = "resolved"
    CLOSED = "closed"


class AuditAction(StrEnum):
    TICKET_CREATED = "ticket_created"
    ASSIGNED = "assigned"
    STATUS_CHANGED = "status_changed"
    COMMENTED = "commented"


# Разрешённые переходы: только вперёд и только на один шаг.
ALLOWED_TRANSITIONS: dict[TicketStatus, TicketStatus] = {
    TicketStatus.NEW: TicketStatus.IN_PROGRESS,
    TicketStatus.IN_PROGRESS: TicketStatus.RESOLVED,
    TicketStatus.RESOLVED: TicketStatus.CLOSED,
}


def can_transition(current: TicketStatus, target: TicketStatus) -> bool:
    return ALLOWED_TRANSITIONS.get(current) == target
