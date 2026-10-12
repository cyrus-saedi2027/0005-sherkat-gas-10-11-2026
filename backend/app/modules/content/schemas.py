from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

Tier = Literal["no_cost", "low_cost", "high_cost"]


class ArticleIn(BaseModel):
    title: str = Field(min_length=3, max_length=200)
    slug: str | None = Field(default=None, max_length=80, pattern=r"^[a-z0-9\-]+$")
    summary: str = Field(default="", max_length=500)
    body: str = Field(default="", max_length=50_000)
    category: Literal["tip", "article", "news", "guide"] = "tip"
    target_tiers: list[Tier] = Field(default_factory=list, max_length=3)
    cover_file_id: str | None = Field(default=None, max_length=32)


class ArticleStatusIn(BaseModel):
    status: Literal["draft", "published", "archived"]


class ArticleOut(BaseModel):
    id: int
    slug: str
    title: str
    summary: str
    category: str
    target_tiers: list[str]
    status: str
    published_at: datetime | None
    cover_url: str | None
    reading_minutes: int
    updated_at: datetime


class ArticleDetail(ArticleOut):
    body: str
    cover_file_id: str | None
