from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class Equipment(BaseModel):
    type: Literal["heater", "package", "water_heater", "fireplace", "stove", "other"]
    count: int = Field(ge=1, le=50)
    condition: Literal["good", "fair", "poor"]
    age_years: int | None = Field(default=None, ge=0, le=80)


class ChecklistIn(BaseModel):
    floor_area_m2: float | None = Field(default=None, ge=0, le=100_000)
    built_area_m2: float | None = Field(default=None, ge=0, le=100_000)
    residents_count: int | None = Field(default=None, ge=0, le=100)
    building_type: Literal["apartment", "villa", "other"] | None = None
    heating_equipment: list[Equipment] = Field(default_factory=list, max_length=30)
    insulation: Literal["none", "partial", "full"] | None = None
    window_seals: Literal["none", "poor", "good"] | None = None
    chimney_status: Literal["ok", "needs_repair", "blocked", "none"] | None = None
    notes: str | None = Field(default=None, max_length=3000)


class ChecklistOut(ChecklistIn):
    completed_by: int | None = None
    updated_at: datetime | None = None


class CallIn(BaseModel):
    outcome: Literal["reached", "no_answer", "wrong_number", "callback"]
    note: str | None = Field(default=None, max_length=1000)
    next_call_at: datetime | None = None


class CallOut(BaseModel):
    id: int
    staff_id: int
    called_at: datetime
    outcome: str
    note: str | None
    next_call_at: datetime | None


class EvaluateIn(BaseModel):
    tier: Literal["no_cost", "low_cost", "high_cost"]
    needs_field_visit: bool
    reason: str | None = Field(default=None, max_length=500)


class VisitIn(BaseModel):
    start: datetime
    end: datetime
    note: str | None = Field(default=None, max_length=1000)


class VisitDoneIn(BaseModel):
    outcome: Literal["done", "missed"]
    note: str | None = Field(default=None, max_length=1000)


class VisitOut(BaseModel):
    id: int
    case_id: int
    ambassador_id: int
    ambassador_name: str | None = None
    scheduled_start: datetime
    scheduled_end: datetime
    status: str
    note: str | None
    subscriber_name: str | None = None
    address: str | None = None


class EstimateItem(BaseModel):
    title: str = Field(min_length=2, max_length=160)
    qty: int = Field(ge=1, le=10_000)
    unit_cost_rial: int = Field(ge=0, le=100_000_000_000)


class EstimateIn(BaseModel):
    items: list[EstimateItem] = Field(min_length=1, max_length=50)
    note: str | None = Field(default=None, max_length=1000)


class EstimateOut(BaseModel):
    id: int
    items: list[EstimateItem]
    total_cost_rial: int
    free_cap_rial: int
    subscriber_share_pct: int
    subscriber_share_rial: int
    program_share_rial: int
    status: str
    note: str | None
    created_at: datetime
    responded_at: datetime | None


class PhotoOut(BaseModel):
    id: int
    phase: str
    caption: str | None
    url: str | None
    thumb_url: str | None
    created_at: datetime


class CaseEventOut(BaseModel):
    id: int
    actor_type: str
    actor_id: int | None
    actor_name: str | None = None
    action: str
    from_status: str | None
    to_status: str | None
    note: str | None
    created_at: datetime


class NoteIn(BaseModel):
    note: str | None = Field(default=None, max_length=1000)


class ReasonIn(BaseModel):
    reason: str = Field(min_length=3, max_length=300)


class CloseIn(ReasonIn):
    status: Literal["cancelled", "closed_no_action"]


class AssignIn(BaseModel):
    ambassador_id: int


class OpenCaseIn(BaseModel):
    user_id: int
    priority: Literal["low", "normal", "high"] = "normal"
    note: str | None = Field(default=None, max_length=500)


class CaseOut(BaseModel):
    id: int
    status: str
    tier: str | None
    suggested_tier: str | None
    needs_field_visit: bool | None
    priority: str
    opened_reason: str
    user_id: int
    subscriber_id: int
    subscription_no: str
    subscriber_name: str | None
    mobile_masked: str
    region_id: int | None
    region_name: str | None
    ambassador_id: int | None
    ambassador_name: str | None
    assignment_method: str | None
    assigned_at: datetime | None
    next_visit_at: datetime | None
    created_at: datetime
    updated_at: datetime
    completed_at: datetime | None


class CaseDetail(CaseOut):
    address: str | None
    tier_reason: str | None
    executed: bool
    closed_reason: str | None
    checklist: ChecklistOut | None
    calls: list[CallOut]
    visits: list[VisitOut]
    photos: list[PhotoOut]
    estimates: list[EstimateOut]
    events: list[CaseEventOut]
    baseline_annual_m3: float | None
    allowed_actions: list[str]


class UserCaseOut(BaseModel):
    id: int
    status: str
    tier: str | None
    needs_field_visit: bool | None
    ambassador_name: str | None
    next_visit: VisitOut | None
    estimate: EstimateOut | None
    photos: list[PhotoOut]
    timeline: list[CaseEventOut]
    created_at: datetime
    completed_at: datetime | None


class ConsentIn(BaseModel):
    accept: bool
