"""Paginated list responses. `size` is hard-capped (R36: cap response record count)."""

from __future__ import annotations

from typing import Annotated, Generic, TypeVar

from fastapi import Query
from pydantic import BaseModel
from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session

T = TypeVar("T")
MAX_PAGE_SIZE = 100


class Page(BaseModel, Generic[T]):
    items: list[T]
    total: int
    page: int
    size: int


class PageParams(BaseModel):
    page: int = 1
    size: int = 20

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.size


def page_params(
    page: Annotated[int, Query(ge=1, le=100_000)] = 1,
    size: Annotated[int, Query(ge=1, le=MAX_PAGE_SIZE)] = 20,
) -> PageParams:
    return PageParams(page=page, size=size)


def paginate(db: Session, stmt: Select, params: PageParams) -> tuple[list, int]:
    """Returns (rows, total). Rows are scalars when stmt selects a single entity."""
    total = db.scalar(select(func.count()).select_from(stmt.order_by(None).subquery())) or 0
    rows = list(db.scalars(stmt.limit(params.size).offset(params.offset)).all())
    return rows, int(total)
