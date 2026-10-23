"""УП8. Миграции Alembic: upgrade head → downgrade → повторный upgrade."""

from __future__ import annotations

import pytest
from alembic import command
from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext
from alembic.script import ScriptDirectory
from sqlalchemy import inspect, text

from app.core.database import make_engine
from app.db_migrate import alembic_config
from app.models import Base

APP_TABLES = {"users", "categories", "tickets", "comments", "audit_events"}
SEED = ["IT", "Учебный процесс", "Хозяйственная часть"]


@pytest.fixture
def db_url(tmp_path):
    return f"sqlite:///{(tmp_path / 'migrations.db').as_posix()}"


@pytest.fixture
def cfg(db_url):
    config = alembic_config(db_url)
    config.attributes["configure_logger"] = False  # не перенастраивать логирование pytest
    return config


def _tables(url):
    engine = make_engine(url)
    try:
        return set(inspect(engine).get_table_names()) - {"alembic_version"}
    finally:
        engine.dispose()


def _categories(url):
    engine = make_engine(url)
    try:
        with engine.connect() as conn:
            return sorted(conn.execute(text("SELECT name FROM categories")).scalars())
    finally:
        engine.dispose()


def _current_revision(url):
    engine = make_engine(url)
    try:
        with engine.connect() as conn:
            return MigrationContext.configure(conn).get_current_revision()
    finally:
        engine.dispose()


def test_migration_chain_is_linear():
    script = ScriptDirectory.from_config(alembic_config("sqlite://"))
    assert script.get_heads() == ["0002_seed_categories"]
    revisions = [r.revision for r in script.walk_revisions("base", "heads")]
    assert revisions == ["0002_seed_categories", "0001_initial"]


def test_upgrade_head_creates_schema_and_three_categories(cfg, db_url):
    command.upgrade(cfg, "head")
    assert _tables(db_url) == APP_TABLES
    assert _categories(db_url) == sorted(SEED)
    assert _current_revision(db_url) == "0002_seed_categories"


def test_downgrade_removes_changes_and_upgrade_again_works(cfg, db_url):
    command.upgrade(cfg, "head")

    command.downgrade(cfg, "-1")  # откат сида
    assert _categories(db_url) == []
    assert _tables(db_url) == APP_TABLES

    command.downgrade(cfg, "base")  # откат схемы
    assert _tables(db_url) == set()
    assert _current_revision(db_url) is None

    command.upgrade(cfg, "head")  # повторный upgrade без ручной правки БД
    assert _tables(db_url) == APP_TABLES
    assert _categories(db_url) == sorted(SEED)


def test_seed_migration_is_idempotent_with_existing_category(cfg, db_url):
    command.upgrade(cfg, "0001_initial")
    engine = make_engine(db_url)
    with engine.begin() as conn:
        conn.execute(text("INSERT INTO categories (name) VALUES ('IT')"))
    engine.dispose()
    command.upgrade(cfg, "head")
    assert _categories(db_url) == sorted(SEED)


def test_migrations_match_orm_models(cfg, db_url):
    """После upgrade head схема БД совпадает с моделями (autogenerate не видит различий)."""
    command.upgrade(cfg, "head")
    engine = make_engine(db_url)
    try:
        with engine.connect() as conn:
            ctx = MigrationContext.configure(conn, opts={"compare_type": True})
            diff = compare_metadata(ctx, Base.metadata)
    finally:
        engine.dispose()
    assert diff == []


def test_foreign_keys_created_by_migration(cfg, db_url):
    command.upgrade(cfg, "head")
    engine = make_engine(db_url)
    try:
        fks = inspect(engine).get_foreign_keys("tickets")
    finally:
        engine.dispose()
    by_col = {fk["constrained_columns"][0]: (fk["referred_table"], fk["options"].get("ondelete")) for fk in fks}
    assert by_col == {
        "author_id": ("users", "RESTRICT"),
        "assignee_id": ("users", "SET NULL"),
        "category_id": ("categories", "RESTRICT"),
    }
