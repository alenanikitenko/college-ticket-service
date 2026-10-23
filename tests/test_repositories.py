"""УП9. Репозитории и транзакции."""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

from app.core.errors import NotFoundError, PermissionDeniedError
from app.models import AuditAction, AuditEvent, Category, Comment, Ticket, TicketStatus, User, UserRole
from app.repositories import (
    AuditEventRepository,
    CategoryRepository,
    CommentRepository,
    TicketFilter,
    TicketRepository,
    UserRepository,
)
from app.schemas.ticket import TicketCreate
from app.services import TicketService, transaction

REPO_DIR = Path(__file__).resolve().parents[1] / "app" / "repositories"


def _seed(session):
    users = UserRepository(session)
    student = users.add(User(email="s@college.edu", full_name="Студент", password_hash="h"))
    operator = users.add(User(email="o@college.edu", full_name="Оператор", role=UserRole.OPERATOR,
                              password_hash="h"))
    category = CategoryRepository(session).add(Category(name="IT"))
    session.commit()
    return student, operator, category


# --- требования к слою -----------------------------------------------------------

def test_five_repositories_exist():
    files = {p.stem for p in REPO_DIR.glob("*.py")} - {"__init__", "base"}
    assert files == {"user", "category", "ticket", "comment", "audit_event"}


@pytest.mark.parametrize("path", sorted(REPO_DIR.glob("*.py")), ids=lambda p: p.name)
def test_repository_does_not_import_fastapi_and_does_not_commit(path):
    tree = ast.parse(path.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            assert all(not a.name.startswith(("fastapi", "starlette")) for a in node.names)
        if isinstance(node, ast.ImportFrom):
            assert not (node.module or "").startswith(("fastapi", "starlette"))
        if isinstance(node, ast.Attribute):
            assert node.attr not in {"commit", "rollback"}, f"{path.name}: commit/rollback — задача сервиса"


# --- базовые операции пяти репозиториев ------------------------------------------

def test_user_repository_crud(db_session):
    repo = UserRepository(db_session)
    user = repo.add(User(email="a@college.edu", full_name="Анна", password_hash="h"))
    assert user.id is not None
    assert repo.get(user.id) is user
    assert repo.get_by_email("  A@College.edu ") is user
    assert repo.count() == 1
    assert repo.list_filtered(role=UserRole.STUDENT) == [user]
    assert repo.list_filtered(role=UserRole.ADMIN) == []
    repo.delete(user)
    assert repo.get(user.id) is None


def test_category_repository_crud(db_session):
    repo = CategoryRepository(db_session)
    it = repo.add(Category(name="IT"))
    repo.add(Category(name="Библиотека"))
    assert repo.get_by_name("IT") is it
    assert [c.name for c in repo.list()] == ["IT", "Библиотека"]
    assert repo.has_tickets(it.id) is False


def test_ticket_repository_filtering(db_session):
    student, operator, category = _seed(db_session)
    repo = TicketRepository(db_session)
    t1 = repo.add(Ticket(title="Первая", description="d", priority=1, author_id=student.id,
                         category_id=category.id))
    t2 = repo.add(Ticket(title="Вторая", description="d", priority=5, author_id=student.id,
                         category_id=category.id, assignee_id=operator.id,
                         status=TicketStatus.IN_PROGRESS))
    assert repo.list_filtered(TicketFilter()) == [t1, t2]
    assert repo.list_filtered(TicketFilter(status=TicketStatus.NEW)) == [t1]
    assert repo.list_filtered(TicketFilter(priority=5)) == [t2]
    assert repo.list_filtered(TicketFilter(assignee_id=operator.id)) == [t2]
    assert repo.list_filtered(TicketFilter(visible_to_operator_id=operator.id)) == [t1, t2]
    assert repo.list_filtered(TicketFilter(), limit=1, offset=1) == [t2]
    assert CategoryRepository(db_session).has_tickets(category.id) is True


def test_comment_and_audit_repositories(db_session):
    student, _, category = _seed(db_session)
    ticket = TicketRepository(db_session).add(
        Ticket(title="Тема", description="d", priority=2, author_id=student.id, category_id=category.id)
    )
    comments = CommentRepository(db_session)
    c = comments.add(Comment(ticket_id=ticket.id, author_id=student.id, text="Привет"))
    assert comments.list_for_ticket(ticket.id) == [c]
    audit = AuditEventRepository(db_session)
    e1 = audit.record(ticket_id=ticket.id, actor_id=student.id, action=AuditAction.TICKET_CREATED)
    e2 = audit.record(ticket_id=ticket.id, actor_id=student.id, action=AuditAction.COMMENTED)
    assert audit.list_for_ticket(ticket.id) == [e1, e2]


# --- транзакции -------------------------------------------------------------------

def test_service_commits_ticket_and_audit_together(db_session):
    student, _, category = _seed(db_session)
    ticket = TicketService(db_session).create_ticket(
        student, TicketCreate(title="Нет сети", description="Ауд. 214", priority=3, category_id=category.id)
    )
    db_session.expire_all()
    assert db_session.get(Ticket, ticket.id).status == TicketStatus.NEW
    events = AuditEventRepository(db_session).list_for_ticket(ticket.id)
    assert [e.action for e in events] == [AuditAction.TICKET_CREATED]


def test_rollback_leaves_no_partial_data(db_session, monkeypatch):
    """Заявка записана (flush), но запись аудита падает → откатывается всё."""
    student, _, category = _seed(db_session)

    def broken_record(self, **kwargs):
        raise RuntimeError("сбой записи аудита")

    monkeypatch.setattr(AuditEventRepository, "record", broken_record)
    service = TicketService(db_session)
    with pytest.raises(RuntimeError, match="сбой записи аудита"):
        service.create_ticket(
            student, TicketCreate(title="Нет сети", description="d", priority=3, category_id=category.id)
        )
    db_session.expire_all()
    assert db_session.query(Ticket).count() == 0
    assert db_session.query(AuditEvent).count() == 0
    # Сессия после rollback работоспособна
    assert db_session.query(User).count() == 2


def test_transaction_helper_rolls_back_on_exception(db_session):
    with pytest.raises(ValueError):
        with transaction(db_session):
            UserRepository(db_session).add(User(email="tmp@college.edu", full_name="Врем", password_hash="h"))
            raise ValueError("ошибка в середине транзакции")
    assert UserRepository(db_session).get_by_email("tmp@college.edu") is None


def test_service_rejects_non_student_and_unknown_category(db_session):
    student, operator, category = _seed(db_session)
    service = TicketService(db_session)
    data = TicketCreate(title="Тема", description="d", priority=3, category_id=category.id)
    with pytest.raises(PermissionDeniedError):
        service.create_ticket(operator, data)
    with pytest.raises(NotFoundError):
        service.create_ticket(student, data.model_copy(update={"category_id": 999}))
    assert db_session.query(Ticket).count() == 0
