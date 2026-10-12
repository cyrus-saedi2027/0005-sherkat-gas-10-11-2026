from __future__ import annotations

from pydantic import BaseModel, Field


class RegionOut(BaseModel):
    id: int
    name: str
    code: str
    parent_id: int | None
    is_active: bool


class RegionIn(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    code: str = Field(min_length=1, max_length=32, pattern=r"^[A-Za-z0-9_\-]+$")
    parent_id: int | None = None
    is_active: bool = True
