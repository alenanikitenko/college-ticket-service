"""Начальные категории: «IT», «Учебный процесс», «Хозяйственная часть».

Revision ID: 0002_seed_categories
Revises: 0001_initial
Create Date: 2026-10-24
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0002_seed_categories"
down_revision: str | None = "0001_initial"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

INITIAL_CATEGORIES = ("IT", "Учебный процесс", "Хозяйственная часть")

categories = sa.table("categories", sa.column("id", sa.Integer), sa.column("name", sa.String))


def upgrade() -> None:
    conn = op.get_bind()
    existing = set(conn.execute(sa.select(categories.c.name)).scalars())
    rows = [{"name": name} for name in INITIAL_CATEGORIES if name not in existing]
    if rows:
        op.bulk_insert(categories, rows)


def downgrade() -> None:
    op.execute(categories.delete().where(categories.c.name.in_(INITIAL_CATEGORIES)))
