from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class BalanceOut(BaseModel):
    available: int
    pending: int
    suspended: int
    total: int
    rial_rate: int
    available_rial: int
    next_release_at: datetime | None


class LedgerOut(BaseModel):
    id: int
    event_type: str
    event_title: str
    amount: int
    status: str
    reason: str
    ref_type: str | None
    ref_id: str | None
    period_key: str | None
    available_at: datetime | None
    created_at: datetime
    suspended_reason: str | None = None


class LedgerPage(BaseModel):
    items: list[LedgerOut]
    total: int
    page: int
    size: int


class RuleOut(BaseModel):
    event_type: str
    title_fa: str
    points: int
    is_active: bool
    per_unit: bool
    monthly_cap_points: int | None


class RuleUpdate(BaseModel):
    points: int = Field(ge=0, le=100_000)
    is_active: bool
    monthly_cap_points: int | None = Field(default=None, ge=0, le=10_000_000)
    title_fa: str | None = Field(default=None, min_length=2, max_length=120)


class AdjustIn(BaseModel):
    user_id: int
    amount: int = Field(ge=-1_000_000, le=1_000_000)
    reason: str = Field(min_length=3, max_length=300)


class SuspendIn(BaseModel):
    reason: str = Field(min_length=3, max_length=300)


class UnsuspendIn(BaseModel):
    reverse: bool = False
