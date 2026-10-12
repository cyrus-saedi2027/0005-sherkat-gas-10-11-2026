from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

Status = Literal["open", "in_progress", "awaiting_customer", "answered", "resolved", "closed"]
Priority = Literal["low", "normal", "high", "urgent"]
Unit = Literal["support", "technical", "finance", "ambassador"]


class AttachmentOut(BaseModel):
    id: int
    kind: str
    url: str | None
    thumb_url: str | None


class MessageOut(BaseModel):
    id: int
    author_type: str
    author_name: str | None
    body: str
    is_internal: bool
    attachments: list[AttachmentOut]
    created_at: datetime


class TicketOut(BaseModel):
    id: int
    tracking_code: str
    subject_key: str
    subject_fa: str
    title: str
    status: str
    priority: str
    assigned_unit: str
    rating: int | None
    created_at: datetime
    updated_at: datetime
    closed_at: datetime | None


class AdminTicketOut(TicketOut):
    user_id: int
    user_name: str | None
    subscription_no: str | None
    assignee_staff_id: int | None
    assignee_name: str | None
    follow_up_at: datetime | None
    last_customer_activity_at: datetime | None
    last_staff_activity_at: datetime | None
    overdue_follow_up: bool


class TicketDetail(TicketOut):
    messages: list[MessageOut]
    rating_comment: str | None
    can_reply: bool
    can_rate: bool


class EventOut(BaseModel):
    field: str
    old: str | None
    new: str | None
    actor_name: str | None
    created_at: datetime


class AdminTicketDetail(AdminTicketOut):
    messages: list[MessageOut]
    events: list[EventOut]
    rating_comment: str | None


class TicketUpdateIn(BaseModel):
    status: Status | None = None
    priority: Priority | None = None
    unit: Unit | None = None
    assignee_id: int | None = None
    clear_assignee: bool = False
    follow_up_at: datetime | None = None
    clear_follow_up: bool = False


class RateIn(BaseModel):
    rating: int = Field(ge=1, le=5)
    comment: str | None = Field(default=None, max_length=500)
