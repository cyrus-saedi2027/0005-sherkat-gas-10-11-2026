from __future__ import annotations

from datetime import datetime

from sqlalchemy import JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base, Timestamped


class Article(Timestamped, Base):
    """Educational / informational content (R17–R19, R46). Body is Markdown, rendered as text-only on clients."""

    __tablename__ = "content_articles"
    slug: Mapped[str] = mapped_column(String(80), unique=True)
    title: Mapped[str] = mapped_column(String(200))
    summary: Mapped[str] = mapped_column(String(500), default="")
    body: Mapped[str] = mapped_column(Text, default="")
    cover_file_id: Mapped[str | None] = mapped_column(String(32))
    category: Mapped[str] = mapped_column(String(16), default="tip", index=True)  # tip | article | news | guide
    target_tiers: Mapped[list[str]] = mapped_column(JSON, default=list)  # empty = everyone
    status: Mapped[str] = mapped_column(String(12), default="draft", index=True)  # draft | published | archived
    published_at: Mapped[datetime | None] = mapped_column(index=True)
    author_id: Mapped[int | None]
    reading_minutes: Mapped[int] = mapped_column(default=2)
