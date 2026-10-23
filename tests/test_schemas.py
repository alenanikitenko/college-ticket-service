"""УП10. Схемы Pydantic: граничные значения каждого ограничения."""

from __future__ import annotations

import pytest
from pydantic import BaseModel, ValidationError

import app.schemas as schemas_pkg
from app.schemas import (
    OUTPUT_SCHEMAS,
    CommentCreate,
    TicketCreate,
    UserRead,
    UserRegister,
)

VALID_USER = {"email": "user1@college.edu", "full_name": "Иван Петров", "password": "Secret123!"}
VALID_TICKET = {"title": "Нет сети", "description": "Ауд. 214", "priority": 3, "category_id": 1}


def _ok(model, **fields):
    return model(**fields)


def _fails(model, field, **fields):
    with pytest.raises(ValidationError) as exc_info:
        model(**fields)
    assert field in {str(e["loc"][0]) for e in exc_info.value.errors()}


# --- email -------------------------------------------------------------------------

@pytest.mark.parametrize("email", ["user1@college.edu", "a.b-c@sub.college.ru", "USER2@College.EDU"])
def test_valid_email_accepted(email):
    user = _ok(UserRegister, **{**VALID_USER, "email": email})
    assert user.email == email.lower()


@pytest.mark.parametrize("email", ["", "user1", "user1@", "@college.edu", "user1@college", "a b@college.edu"])
def test_invalid_email_rejected(email):
    _fails(UserRegister, "email", **{**VALID_USER, "email": email})


# --- full_name: 2–100 -------------------------------------------------------------

@pytest.mark.parametrize(("length", "valid"), [(1, False), (2, True), (100, True), (101, False)])
def test_full_name_bounds(length, valid):
    data = {**VALID_USER, "full_name": "Я" * length}
    if valid:
        assert len(_ok(UserRegister, **data).full_name) == length
    else:
        _fails(UserRegister, "full_name", **data)


def test_full_name_of_spaces_is_rejected():
    _fails(UserRegister, "full_name", **{**VALID_USER, "full_name": "   "})


# --- title: 3–100 -----------------------------------------------------------------

@pytest.mark.parametrize(("length", "valid"), [(2, False), (3, True), (100, True), (101, False)])
def test_title_bounds(length, valid):
    data = {**VALID_TICKET, "title": "т" * length}
    if valid:
        assert len(_ok(TicketCreate, **data).title) == length
    else:
        _fails(TicketCreate, "title", **data)


# --- description: 1–2000 ----------------------------------------------------------

@pytest.mark.parametrize(("length", "valid"), [(0, False), (1, True), (2000, True), (2001, False)])
def test_description_bounds(length, valid):
    data = {**VALID_TICKET, "description": "d" * length}
    if valid:
        assert len(_ok(TicketCreate, **data).description) == length
    else:
        _fails(TicketCreate, "description", **data)


# --- priority: 1–5 ----------------------------------------------------------------

@pytest.mark.parametrize(("value", "valid"), [(0, False), (1, True), (5, True), (6, False)])
def test_priority_bounds(value, valid):
    data = {**VALID_TICKET, "priority": value}
    if valid:
        assert _ok(TicketCreate, **data).priority == value
    else:
        _fails(TicketCreate, "priority", **data)


def test_priority_defaults_to_3():
    data = {k: v for k, v in VALID_TICKET.items() if k != "priority"}
    assert TicketCreate(**data).priority == 3


# --- текст комментария: 1–1000 ----------------------------------------------------

@pytest.mark.parametrize(("length", "valid"), [(0, False), (1, True), (1000, True), (1001, False)])
def test_comment_text_bounds(length, valid):
    if valid:
        assert len(_ok(CommentCreate, text="к" * length).text) == length
    else:
        _fails(CommentCreate, "text", text="к" * length)


# --- пароль: 8–128 ----------------------------------------------------------------

@pytest.mark.parametrize(("length", "valid"), [(7, False), (8, True), (128, True), (129, False)])
def test_password_bounds(length, valid):
    data = {**VALID_USER, "password": "p" * length}
    if valid:
        _ok(UserRegister, **data)
    else:
        _fails(UserRegister, "password", **data)


def test_register_forbids_role_field():
    _fails(UserRegister, "role", **{**VALID_USER, "role": "admin"})


# --- password_hash отсутствует во всех выходных схемах -----------------------------

def _all_schema_classes():
    return [obj for obj in vars(schemas_pkg).values()
            if isinstance(obj, type) and issubclass(obj, BaseModel)]


@pytest.mark.parametrize("schema", OUTPUT_SCHEMAS, ids=lambda s: s.__name__)
def test_output_schema_has_no_password_fields(schema):
    fields = set(schema.model_fields)
    assert "password_hash" not in fields
    assert "password" not in fields
    assert "password_hash" not in str(schema.model_json_schema())


def test_no_exported_schema_exposes_password_hash():
    for schema in _all_schema_classes():
        assert "password_hash" not in schema.model_fields, schema.__name__


def test_user_read_from_orm_drops_password_hash():
    from datetime import UTC, datetime

    from app.models import User, UserRole

    orm_user = User(id=1, email="user1@college.edu", full_name="Иван Петров", role=UserRole.STUDENT,
                    password_hash="scrypt$secret", is_active=True, created_at=datetime.now(UTC))
    dumped = UserRead.model_validate(orm_user).model_dump()
    assert "password_hash" not in dumped
    assert dumped["email"] == "user1@college.edu"
