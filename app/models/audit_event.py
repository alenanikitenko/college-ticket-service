from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.column_types import UTCDateTime, str_enum, utcnow
from app.models.enums import AuditAction

if TYPE_CHECKING:
    from app.models.ticket import Ticket
    from app.models.user import User


class AuditEvent(Base):
    __tablename__ = "audit_events"

    id: Mapped[int] = mapped_column(primary_key=True)
    ticket_id: Mapped[int] = mapped_column(
        ForeignKey("tickets.id", ondelete="CASCADE"), nullable=False, index=True
    )
    actor_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    action: Mapped[AuditAction] = mapped_column(
        str_enum(AuditAction, "audit_action", length=50), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), nullable=False, default=utcnow)

    ticket: Mapped[Ticket] = relationship(back_populates="audit_events")
    actor: Mapped[User] = relationship()
