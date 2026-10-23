"""ORM-модели. Импорт пакета регистрирует все пять таблиц в ``Base.metadata``."""

from app.core.database import Base
from app.models.audit_event import AuditEvent
from app.models.category import Category
from app.models.comment import Comment
from app.models.enums import ALLOWED_TRANSITIONS, AuditAction, TicketStatus, UserRole, can_transition
from app.models.ticket import Ticket
from app.models.user import User

__all__ = [
    "ALLOWED_TRANSITIONS",
    "AuditAction",
    "AuditEvent",
    "Base",
    "Category",
    "Comment",
    "Ticket",
    "TicketStatus",
    "User",
    "UserRole",
    "can_transition",
]
