from __future__ import annotations

from sqlalchemy import select

from app.models import Comment
from app.repositories.base import BaseRepository


class CommentRepository(BaseRepository[Comment]):
    model = Comment

    def list_for_ticket(self, ticket_id: int) -> list[Comment]:
        stmt = select(Comment).where(Comment.ticket_id == ticket_id).order_by(Comment.id)
        return list(self.session.scalars(stmt))
