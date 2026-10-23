"""Pydantic-схемы входа и выхода API."""

from app.schemas.audit import AuditEventRead
from app.schemas.category import CategoryCreate, CategoryRead, CategoryUpdate
from app.schemas.comment import CommentCreate, CommentRead
from app.schemas.common import ErrorBody, ErrorResponse, HealthResponse
from app.schemas.report import ReportSummary
from app.schemas.ticket import TicketAssign, TicketCreate, TicketRead, TicketStatusUpdate
from app.schemas.user import LoginRequest, TokenResponse, UserAdminUpdate, UserRead, UserRegister

# Схемы, которые уходят клиенту. Тест проверяет, что ни в одной нет password_hash.
OUTPUT_SCHEMAS = (
    UserRead,
    TokenResponse,
    CategoryRead,
    TicketRead,
    CommentRead,
    AuditEventRead,
    ReportSummary,
    ErrorResponse,
    HealthResponse,
)

__all__ = [
    "OUTPUT_SCHEMAS",
    "AuditEventRead",
    "CategoryCreate",
    "CategoryRead",
    "CategoryUpdate",
    "CommentCreate",
    "CommentRead",
    "ErrorBody",
    "ErrorResponse",
    "HealthResponse",
    "LoginRequest",
    "ReportSummary",
    "TicketAssign",
    "TicketCreate",
    "TicketRead",
    "TicketStatusUpdate",
    "TokenResponse",
    "UserAdminUpdate",
    "UserRead",
    "UserRegister",
]
