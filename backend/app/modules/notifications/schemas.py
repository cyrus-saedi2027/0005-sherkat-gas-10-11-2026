from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class NotificationOut(BaseModel):
    id: int
    kind: str
    title: str
    body: str
    data: dict[str, Any]
    read_at: datetime | None
    created_at: datetime


class NotificationPage(BaseModel):
    items: list[NotificationOut]
    total: int
    unread: int
    page: int
    size: int


class MarkRead(BaseModel):
    ids: list[int] | None = Field(default=None, max_length=500)
