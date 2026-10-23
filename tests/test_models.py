"""УП7. ORM-модели: пять таблиц, PK/FK/unique, создание схемы во временной SQLite."""

from __future__ import annotations

import pytest
from sqlalchemy import inspect
from sqlalchemy.exc import IntegrityError, StatementError

from app.core.database import make_engine, make_session_factory
from app.models import (
    AuditAction,
    AuditEvent,
    Base,
    Category,
    Comment,
    Ticket,
    TicketStatus,
    User,
    UserRole,
)

EXPECTED_TABLES = {"users", "categories", "tickets", "comments", "audit_events"}


def _fk_map(table):
    return {fk.parent.name: (fk.column.table.name, fk.column.name, fk.ondelete) for fk in table.foreign_keys}


def test_metadata_contains_exactly_five_tables():
    assert set(Base.metadata.tables) == EXPECTED_TABLES


@pytest.mark.parametrize("table", sorted(EXPECTED_TABLES))
def test_every_table_has_integer_id_primary_key(table):
    pk = [c.name for c in Base.metadata.tables[table].primary_key.columns]
    assert pk == ["id"]


def test_foreign_keys_and_on_delete_rules():
    t = Base.metadata.tables
    assert _fk_map(t["tickets"]) == {
        "author_id": ("users", "id", "RESTRICT"),
        "assignee_id": ("users", "id", "SET NULL"),
        "category_id": ("categories", "id", "RESTRICT"),
    }
    assert _fk_map(t["comments"]) == {
        "ticket_id": ("tickets", "id", "CASCADE"),
        "author_id": ("users", "id", "RESTRICT"),
    }
    assert _fk_map(t["audit_events"]) == {
        "ticket_id": ("tickets", "id", "CASCADE"),
        "actor_id": ("users", "id", "RESTRICT"),
    }


def test_unique_constraints_and_nullability():
    t = Base.metadata.tables
    assert t["users"].c.email.unique is True
    assert t["categories"].c.name.unique is True
    assert t["tickets"].c.assignee_id.nullable is True
    assert t["tickets"].c.author_id.nullable is False
    for name, table in t.items():
        for column in table.columns:
            if not (name == "tickets" and column.name == "assignee_id"):
                assert column.nullable is False, f"{name}.{column.name} должен быть NOT NULL"


def test_enums_have_required_values():
    assert {r.value for r in UserRole} == {"student", "operator", "admin"}
    assert {s.value for s in TicketStatus} == {"new", "in_progress", "resolved", "closed"}


def test_schema_is_created_in_temporary_sqlite(tmp_path):
    engine = make_engine(f"sqlite:///{(tmp_path / 'schema.db').as_posix()}")
    Base.metadata.create_all(engine)
    insp = inspect(engine)
    assert set(insp.get_table_names()) == EXPECTED_TABLES
    assert {fk["referred_table"] for fk in insp.get_foreign_keys("tickets")} == {"users", "categories"}
    unique_cols = {tuple(u["column_names"]) for u in insp.get_unique_constraints("categories")}
    assert ("name",) in unique_cols
    email_indexes = [i for i in insp.get_indexes("users") if i["column_names"] == ["email"]]
    assert email_indexes and email_indexes[0]["unique"]
    engine.dispose()


def _make_graph(session):
    student = User(email="s@college.edu", full_name="Студент", role=UserRole.STUDENT, password_hash="x")
    operator = User(email="o@college.edu", full_name="Оператор", role=UserRole.OPERATOR, password_hash="x")
    category = Category(name="IT")
    session.add_all([student, operator, category])
    session.flush()
    ticket = Ticket(title="Нет сети", description="Ауд. 214", priority=3,
                    author=student, assignee=operator, category=category)
    session.add(ticket)
    session.flush()
    session.add_all([
        Comment(ticket_id=ticket.id, author_id=student.id, text="Срочно"),
        AuditEvent(ticket_id=ticket.id, actor_id=student.id, action=AuditAction.TICKET_CREATED),
    ])
    session.commit()
    return student, operator, category, ticket


def test_relationships_defaults_and_timestamps(db_session):
    student, operator, category, ticket = _make_graph(db_session)
    db_session.refresh(ticket)
    assert ticket.status == TicketStatus.NEW
    assert ticket.author.email == "s@college.edu"
    assert ticket.assignee.role == UserRole.OPERATOR
    assert ticket.category.name == "IT"
    assert len(ticket.comments) == 1 and len(ticket.audit_events) == 1
    assert student.is_active is True and student.role == UserRole.STUDENT
    assert ticket.created_at.tzinfo is not None


def test_unique_email_is_enforced_by_db(db_session):
    db_session.add(User(email="dup@college.edu", full_name="Первый", password_hash="x"))
    db_session.commit()
    db_session.add(User(email="dup@college.edu", full_name="Второй", password_hash="x"))
    with pytest.raises(IntegrityError):
        db_session.commit()


def test_foreign_keys_are_enforced_in_sqlite(db_session):
    db_session.add(Ticket(title="abc", description="d", priority=1, author_id=999, category_id=999))
    with pytest.raises(IntegrityError):
        db_session.commit()


def test_priority_check_constraint(db_session):
    student, _, category, _ = _make_graph(db_session)
    db_session.add(Ticket(title="abc", description="d", priority=9, author_id=student.id,
                          category_id=category.id))
    with pytest.raises(IntegrityError):
        db_session.commit()


def test_invalid_enum_value_is_rejected(db_session):
    db_session.add(User(email="bad@college.edu", full_name="Плохая роль", role="superuser",
                        password_hash="x"))
    with pytest.raises((StatementError, LookupError, ValueError)):
        db_session.commit()


def test_cascade_and_set_null_on_delete(engine):
    session = make_session_factory(engine)()
    student, operator, category, ticket = _make_graph(session)
    ticket_id = ticket.id
    # Удаление исполнителя → assignee_id = NULL
    session.delete(operator)
    session.commit()
    session.expire_all()
    assert session.get(Ticket, ticket_id).assignee_id is None
    # Удаление заявки → комментарии и аудит удаляются каскадно
    session.delete(session.get(Ticket, ticket_id))
    session.commit()
    assert session.query(Comment).count() == 0
    assert session.query(AuditEvent).count() == 0
    session.close()
