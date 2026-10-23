from __future__ import annotations

from sqlalchemy import select

from app.models import User, UserRole
from app.repositories.base import BaseRepository


class UserRepository(BaseRepository[User]):
    model = User

    def get_by_email(self, email: str) -> User | None:
        return self.session.scalar(select(User).where(User.email == email.strip().lower()))

    def list_filtered(
        self, *, role: UserRole | None = None, is_active: bool | None = None,
        limit: int = 100, offset: int = 0,
    ) -> list[User]:
        stmt = select(User)
        if role is not None:
            stmt = stmt.where(User.role == role)
        if is_active is not None:
            stmt = stmt.where(User.is_active == is_active)
        return list(self.session.scalars(stmt.order_by(User.id).limit(limit).offset(offset)))
