from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import JSON, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base, Timestamped


class Survey(Timestamped, Base):
    __tablename__ = "surveys"
    title: Mapped[str] = mapped_column(String(200))
    description: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(10), default="draft", index=True)  # draft | active | closed
    starts_at: Mapped[datetime | None]
    ends_at: Mapped[datetime | None]
    target_tiers: Mapped[list[str]] = mapped_column(JSON, default=list)
    created_by: Mapped[int | None]


class SurveyQuestion(Timestamped, Base):
    __tablename__ = "survey_questions"
    survey_id: Mapped[int] = mapped_column(ForeignKey("surveys.id", ondelete="CASCADE"), index=True)
    kind: Mapped[str] = mapped_column(String(8))  # single | multi | text | rating
    text: Mapped[str] = mapped_column(String(500))
    options: Mapped[list[str]] = mapped_column(JSON, default=list)
    required: Mapped[bool] = mapped_column(default=True)
    sort: Mapped[int] = mapped_column(default=0)


class SurveyResponse(Timestamped, Base):
    __tablename__ = "survey_responses"
    __table_args__ = (UniqueConstraint("survey_id", "user_id"),)
    survey_id: Mapped[int] = mapped_column(ForeignKey("surveys.id", ondelete="CASCADE"), index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    answers: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
