from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.enums import TicketStatus
from app.models.column_types import UTCDateTime, str_enum, utcnow

if TYPE_CHECKING:
    from app.models.audit_event import AuditEvent
    from app.models.category import Category
    from app.models.comment import Comment
    from app.models.user import User


class Ticket(Base):
    __tablename__ = "tickets"
    __table_args__ = (CheckConstraint("priority BETWEEN 1 AND 5", name="priority_range"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[TicketStatus] = mapped_column(
        str_enum(TicketStatus, "ticket_status"), nullable=False, index=True,
        default=TicketStatus.NEW, server_default=TicketStatus.NEW.value,
    )
    priority: Mapped[int] = mapped_column(Integer, nullable=False, default=3, server_default="3")
    author_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    assignee_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    category_id: Mapped[int] = mapped_column(
        ForeignKey("categories.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), nullable=False, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        UTCDateTime(), nullable=False, default=utcnow, onupdate=utcnow
    )

    author: Mapped[User] = relationship(back_populates="authored_tickets", foreign_keys=[author_id])
    assignee: Mapped[User | None] = relationship(
        back_populates="assigned_tickets", foreign_keys=[assignee_id]
    )
    category: Mapped[Category] = relationship(back_populates="tickets")
    comments: Mapped[list[Comment]] = relationship(
        back_populates="ticket", cascade="all, delete-orphan", passive_deletes=True,
        order_by="Comment.id",
    )
    audit_events: Mapped[list[AuditEvent]] = relationship(
        back_populates="ticket", cascade="all, delete-orphan", passive_deletes=True,
        order_by="AuditEvent.id",
    )

    def __repr__(self) -> str:
        return f"<Ticket id={self.id} status={self.status} title={self.title!r}>"
