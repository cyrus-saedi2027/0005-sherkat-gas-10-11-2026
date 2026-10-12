from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, Field
from sqlalchemy import func, select

from app.core.deps import DB, CurrentStaff, StaffCtx, require
from app.core.pagination import Page, PageParams, page_params
from app.core.rbac import P
from app.modules.notifications import broadcast, service
from app.modules.notifications.models import Broadcast
from app.modules.notifications.schemas import MarkRead, NotificationOut, NotificationPage

router = APIRouter(prefix="/notifications", tags=["admin:notifications"])


@router.get("", response_model=NotificationPage)
def my_notifications(staff: CurrentStaff, db: DB, p: PageParams = Depends(page_params), unread: bool = False):
    rows, total, n_unread = service.list_for(db, "staff", staff.id, p.size, p.offset, unread)
    return NotificationPage(items=[NotificationOut.model_validate(r, from_attributes=True) for r in rows],
                            total=total, unread=n_unread, page=p.page, size=p.size)


@router.post("/read")
def mark_read(body: MarkRead, staff: CurrentStaff, db: DB) -> dict[str, int]:
    return {"updated": service.mark_read(db, "staff", staff.id, body.ids)}


class Segment(BaseModel):
    region_ids: list[int] = Field(default_factory=list, max_length=100)
    tiers: list[Literal["no_cost", "low_cost", "high_cost", "none"]] = Field(default_factory=list, max_length=4)
    eligibility: Literal["eligible", "below_threshold"] | None = None


class BroadcastIn(BaseModel):
    title: str = Field(min_length=3, max_length=160)
    body: str = Field(default="", max_length=1000)
    channels: list[Literal["in_app", "sms"]] = Field(min_length=1, max_length=2)
    segment: Segment = Field(default_factory=Segment)
    route: str | None = Field(default=None, max_length=120, pattern=r"^/[a-z0-9/_\-]*$")


class BroadcastOut(BaseModel):
    id: int
    title: str
    body: str
    channels: list[str]
    segment: dict[str, Any]
    route: str | None
    recipients: int
    created_by: int
    created_at: datetime


@router.post("/broadcasts/preview")
def preview(body: Segment, db: DB, _s: StaffCtx = require(P.NOTIFICATIONS_BROADCAST)) -> dict[str, int]:
    return {"recipients": broadcast.count(db, body.model_dump())}


@router.post("/broadcasts", response_model=BroadcastOut, status_code=201)
def send(body: BroadcastIn, request: Request, db: DB, staff: StaffCtx = require(P.NOTIFICATIONS_BROADCAST)) -> BroadcastOut:
    b = broadcast.send(db, title=body.title, body=body.body, channels=list(body.channels), segment=body.segment.model_dump(),
                       route=body.route, actor=staff.actor, request=request)
    return BroadcastOut.model_validate(b, from_attributes=True)


@router.get("/broadcasts", response_model=Page[BroadcastOut])
def history(db: DB, p: PageParams = Depends(page_params), _s: StaffCtx = require(P.NOTIFICATIONS_BROADCAST)) -> Page[BroadcastOut]:
    total = int(db.scalar(select(func.count()).select_from(Broadcast)) or 0)
    rows = db.scalars(select(Broadcast).order_by(Broadcast.id.desc()).limit(p.size).offset(p.offset)).all()
    return Page(items=[BroadcastOut.model_validate(b, from_attributes=True) for b in rows], total=total, page=p.page, size=p.size)
