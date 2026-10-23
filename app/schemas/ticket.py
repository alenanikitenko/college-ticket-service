from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import TicketStatus


class TicketCreate(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    title: str = Field(min_length=3, max_length=100, examples=["Не работает Wi-Fi"])
    description: str = Field(min_length=1, max_length=2000, examples=["В аудитории 214 нет сети"])
    priority: int = Field(default=3, ge=1, le=5, description="1 — низкий, 5 — критичный")
    category_id: int = Field(ge=1, examples=[1])


class TicketRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    description: str
    status: TicketStatus
    priority: int
    author_id: int
    assignee_id: int | None
    category_id: int
    created_at: datetime
    updated_at: datetime


class TicketAssign(BaseModel):
    model_config = ConfigDict(extra="forbid")

    assignee_id: int = Field(ge=1)


class TicketStatusUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: TicketStatus
