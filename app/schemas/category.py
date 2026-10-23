from __future__ import annotations

from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field

CategoryName = Annotated[str, Field(min_length=2, max_length=100, examples=["IT"])]


class CategoryCreate(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    name: CategoryName


class CategoryUpdate(CategoryCreate):
    pass


class CategoryRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
