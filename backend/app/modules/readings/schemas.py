from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel, Field


class FlagOut(BaseModel):
    code: str
    label: str


class ReadingEventOut(BaseModel):
    id: int
    actor_type: str
    actor_id: int | None
    actor_name: str | None = None
    action: str
    from_status: str | None
    to_status: str | None
    old_value: float | None
    new_value: float | None
    reason: str | None
    created_at: datetime


class ReadingOut(BaseModel):
    id: int
    period_key: str
    period_label: str
    revision: int
    kind: str
    is_current: bool
    input_method: str
    declared_value: float
    approved_value: float | None
    reading_date: date
    status: str
    reason_code: str | None
    reason_text: str | None
    review_note: str | None
    user_note: str | None
    consumption_m3: float | None
    baseline_m3: float | None
    reduction_pct: float | None
    photo_url: str | None
    photo_thumb_url: str | None
    created_at: datetime
    reviewed_at: datetime | None
    can_resubmit: bool


class ReadingDetailOut(ReadingOut):
    events: list[ReadingEventOut]
    revisions: list[ReadingOut]


class CurrentPeriodOut(BaseModel):
    period_key: str
    period_label: str
    reading: ReadingOut | None
    can_submit: bool
    submit_kind: str | None  # initial | correction | review_request | None (pending)
    photo_required: bool
    max_back_days: int


class AdminReadingOut(ReadingOut):
    user_id: int
    subscriber_id: int
    subscription_no: str
    subscriber_name: str | None
    region_id: int | None
    region_name: str | None
    flags: list[FlagOut]
    reviewer_id: int | None
    reviewer_name: str | None
    claimed_by: int | None
    exif_taken_at: datetime | None


class HistoryPoint(BaseModel):
    jyear: int
    jmonth: int
    volume_m3: float


class AdminReadingDetailOut(AdminReadingOut):
    events: list[ReadingEventOut]
    revisions: list[ReadingOut]
    history: list[HistoryPoint]
    previous_approved: ReadingOut | None
    baseline_for_period: float | None
    claimed_by_me: bool
    claimed_by_name: str | None


class ApproveIn(BaseModel):
    approved_value: float | None = Field(default=None, ge=0)
    note: str | None = Field(default=None, max_length=1000)


class CloseIn(BaseModel):
    reason_code: str = Field(max_length=40)
    note: str | None = Field(default=None, max_length=1000)


class ReasonOut(BaseModel):
    code: str
    label: str


class QueueStats(BaseModel):
    pending: int
    flagged: int
    needs_correction: int
    approved_today: int
    rejected_today: int
