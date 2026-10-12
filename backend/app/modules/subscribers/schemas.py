from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class SubscriberOut(BaseModel):
    id: int
    subscription_no: str
    full_name: str | None
    mobile_masked: str
    region_id: int | None
    region_name: str | None
    meter_serial: str | None
    is_active: bool
    baseline_annual_m3: float | None
    eligible: bool
    registered: bool
    user_id: int | None


class HistoryYear(BaseModel):
    jyear: int
    months: dict[int, float]
    total: float


class SubscriberDetail(SubscriberOut):
    address: str | None
    history: list[HistoryYear]
    monthly_baseline: dict[int, float]
    threshold_m3: int
    threshold_basis: str
    eligibility_value: float | None


class SubscriberUpdate(BaseModel):
    full_name: str | None = Field(default=None, max_length=160)
    address: str | None = Field(default=None, max_length=500)
    region_id: int | None = None
    meter_serial: str | None = Field(default=None, max_length=40)
    is_active: bool | None = None
    mobile: str | None = Field(default=None, max_length=20)


class ImportBatchOut(BaseModel):
    id: int
    kind: str
    filename: str
    status: str
    row_count: int
    error_count: int
    errors: list[dict[str, Any]]
    summary: dict[str, Any]
    uploaded_by: int | None
    created_at: datetime
    committed_at: datetime | None


class CommitIn(BaseModel):
    skip_errors: bool = False
