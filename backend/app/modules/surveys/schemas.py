from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


class QuestionIn(BaseModel):
    kind: Literal["single", "multi", "text", "rating"]
    text: str = Field(min_length=3, max_length=500)
    options: list[str] = Field(default_factory=list, max_length=12)
    required: bool = True


class SurveyIn(BaseModel):
    title: str = Field(min_length=3, max_length=200)
    description: str = Field(default="", max_length=2000)
    starts_at: datetime | None = None
    ends_at: datetime | None = None
    target_tiers: list[Literal["no_cost", "low_cost", "high_cost"]] = Field(default_factory=list)
    questions: list[QuestionIn] = Field(min_length=1, max_length=30)


class QuestionOut(QuestionIn):
    id: int


class SurveyOut(BaseModel):
    id: int
    title: str
    description: str
    status: str
    starts_at: datetime | None
    ends_at: datetime | None
    target_tiers: list[str]
    questions: list[QuestionOut]
    responses: int = 0
    answered: bool = False
    points: int = 0
    created_at: datetime


class AnswerIn(BaseModel):
    answers: dict[str, Any] = Field(max_length=30)  # question id (as str) → value


class StatusIn(BaseModel):
    status: Literal["draft", "active", "closed"]


class QuestionResult(BaseModel):
    id: int
    text: str
    kind: str
    counts: dict[str, int]
    average: float | None
    texts: list[str]


class SurveyResults(BaseModel):
    survey: SurveyOut
    responses: int
    questions: list[QuestionResult]
