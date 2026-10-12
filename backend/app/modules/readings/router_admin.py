from __future__ import annotations

from datetime import date, datetime, time, timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy import func, select

from app.core import clock, jalali
from app.core import settings_registry as reg
from app.core.deps import DB, StaffCtx, require
from app.core.errors import AppError
from app.core.normalize import normalize_subscription
from app.core.pagination import Page, PageParams, page_params
from app.core.rbac import P
from app.modules.files.models import StoredFile
from app.modules.readings import presenter, service
from app.modules.readings.models import MeterReading
from app.modules.readings.reasons import REJECT_REASONS
from app.modules.readings.schemas import (AdminReadingDetailOut, AdminReadingOut, ApproveIn, CloseIn, FlagOut,
                                          HistoryPoint, QueueStats, ReasonOut)
from app.modules.regions.models import Region
from app.modules.regions.service import descendants
from app.modules.staff.models import StaffUser
from app.modules.subscribers import service as subscribers
from app.modules.subscribers.models import Subscriber

router = APIRouter(prefix="/readings", tags=["admin:readings"])

STATUSES = "^(pending|flagged|needs_correction|approved|rejected|open)$"


def _admin_out(db, r: MeterReading, sub: Subscriber | None, region: Region | None, names: dict[int, str]) -> AdminReadingOut:
    f = db.get(StoredFile, r.photo_file_id) if r.photo_file_id else None
    return AdminReadingOut(
        **presenter.reading_out(r, for_staff=True).model_dump(), user_id=r.user_id, subscriber_id=r.subscriber_id,
        subscription_no=sub.subscription_no if sub else "", subscriber_name=sub.full_name if sub else None,
        region_id=sub.region_id if sub else None, region_name=region.name if region else None,
        flags=[FlagOut(**x) for x in service.flag_labels(r.flags)], reviewer_id=r.reviewer_id,
        reviewer_name=names.get(r.reviewer_id or 0), claimed_by=r.claimed_by,
        exif_taken_at=f.exif_taken_at if f else None,
    )


@router.get("/reasons", response_model=list[ReasonOut])
def reasons(_s: StaffCtx = require(P.READINGS_VIEW)) -> list[ReasonOut]:
    return [ReasonOut(code=k, label=v) for k, v in REJECT_REASONS.items()]


@router.get("/stats", response_model=QueueStats)
def stats(db: DB, _s: StaffCtx = require(P.READINGS_VIEW)) -> QueueStats:
    rows = dict(db.execute(select(MeterReading.status, func.count()).where(MeterReading.is_current.is_(True))
                           .group_by(MeterReading.status)).all())
    today = jalali.to_tehran(clock.now()).date()
    start = datetime.combine(today, time(0), tzinfo=jalali.TEHRAN)

    def _today(status: str) -> int:
        return int(db.scalar(select(func.count()).where(MeterReading.status == status, MeterReading.reviewed_at >= start)) or 0)

    return QueueStats(pending=int(rows.get("pending", 0)), flagged=int(rows.get("flagged", 0)),
                      needs_correction=int(rows.get("needs_correction", 0)), approved_today=_today("approved"),
                      rejected_today=_today("rejected"))


@router.get("", response_model=Page[AdminReadingOut])
def queue(db: DB, p: PageParams = Depends(page_params),
          status: Annotated[str | None, Query(pattern=STATUSES)] = "open",
          region_id: int | None = None, subscription_no: Annotated[str | None, Query(max_length=30)] = None,
          period_key: Annotated[str | None, Query(pattern=r"^\d{4}-\d{2}$")] = None,
          date_from: date | None = None, date_to: date | None = None, reviewer_id: int | None = None,
          flagged_only: bool = False, sort: Annotated[str, Query(pattern="^(oldest|newest)$")] = "oldest",
          _s: StaffCtx = require(P.READINGS_VIEW)) -> Page[AdminReadingOut]:
    stmt = (select(MeterReading, Subscriber, Region)
            .join(Subscriber, Subscriber.id == MeterReading.subscriber_id)
            .outerjoin(Region, Region.id == Subscriber.region_id)
            .where(MeterReading.is_current.is_(True)))
    if status == "open":
        stmt = stmt.where(MeterReading.status.in_(service.OPEN))
    elif status:
        stmt = stmt.where(MeterReading.status == status)
    if flagged_only:
        stmt = stmt.where(MeterReading.status == "flagged")
    if region_id:
        stmt = stmt.where(Subscriber.region_id.in_(descendants(db, region_id)))
    if subscription_no:
        sn = normalize_subscription(subscription_no) or subscription_no
        stmt = stmt.where(Subscriber.subscription_no.startswith(sn))
    if period_key:
        stmt = stmt.where(MeterReading.period_key == period_key)
    if date_from:
        stmt = stmt.where(MeterReading.created_at >= datetime.combine(date_from, time(0), tzinfo=jalali.TEHRAN))
    if date_to:
        stmt = stmt.where(MeterReading.created_at < datetime.combine(date_to + timedelta(days=1), time(0), tzinfo=jalali.TEHRAN))
    if reviewer_id:
        stmt = stmt.where(MeterReading.reviewer_id == reviewer_id)
    stmt = stmt.order_by(MeterReading.created_at.asc() if sort == "oldest" else MeterReading.created_at.desc())
    total = int(db.scalar(select(func.count()).select_from(stmt.order_by(None).subquery())) or 0)
    rows = db.execute(stmt.limit(p.size).offset(p.offset)).all()
    rids = {r.reviewer_id for r, _, _ in rows if r.reviewer_id}
    names = dict(db.execute(select(StaffUser.id, StaffUser.full_name).where(StaffUser.id.in_(rids))).all()) if rids else {}
    return Page(items=[_admin_out(db, r, s, g, names) for r, s, g in rows], total=total, page=p.page, size=p.size)


def _load(db, reading_id: int) -> MeterReading:
    r = db.get(MeterReading, reading_id)
    if r is None:
        raise AppError("not_found", "قرائت پیدا نشد.", 404)
    return r


def _detail(db, r: MeterReading, staff: StaffCtx) -> AdminReadingDetailOut:
    sub = db.get(Subscriber, r.subscriber_id)
    region = db.get(Region, sub.region_id) if sub and sub.region_id else None
    revs = presenter.revisions(db, r)
    ids = {x.reviewer_id for x in revs if x.reviewer_id} | ({r.claimed_by} if r.claimed_by else set())
    names = dict(db.execute(select(StaffUser.id, StaffUser.full_name).where(StaffUser.id.in_(ids))).all()) if ids else {}
    hist = subscribers.history_series(db, r.subscriber_id)
    prev = service.previous_approved(db, r.subscriber_id, r.period_key)
    months = int(reg.get(db, "reading.period_months"))
    base = _admin_out(db, r, sub, region, names)
    return AdminReadingDetailOut(
        **base.model_dump(), events=presenter.events_out(db, [x.id for x in revs], for_staff=True),
        revisions=[presenter.reading_out(x, for_staff=True) for x in revs],
        history=[HistoryPoint(jyear=y, jmonth=m, volume_m3=v) for y, ms in sorted(hist.items()) for m, v in sorted(ms.items())],
        previous_approved=presenter.reading_out(prev, for_staff=True) if prev else None,
        baseline_for_period=subscribers.period_baseline(db, r.subscriber_id, r.period_key, months),
        claimed_by_me=r.claimed_by == staff.id, claimed_by_name=names.get(r.claimed_by or 0),
    )


@router.get("/{reading_id}", response_model=AdminReadingDetailOut)
def detail(reading_id: int, db: DB, staff: StaffCtx = require(P.READINGS_VIEW)) -> AdminReadingDetailOut:
    return _detail(db, _load(db, reading_id), staff)


@router.post("/{reading_id}/claim", response_model=AdminReadingDetailOut)
def claim(reading_id: int, db: DB, staff: StaffCtx = require(P.READINGS_REVIEW)) -> AdminReadingDetailOut:
    r = _load(db, reading_id)
    if r.status in service.OPEN:
        service.claim(db, r, staff.id)
    return _detail(db, r, staff)


@router.post("/{reading_id}/approve", response_model=AdminReadingDetailOut)
def approve(reading_id: int, body: ApproveIn, request: Request, db: DB,
            staff: StaffCtx = require(P.READINGS_REVIEW)) -> AdminReadingDetailOut:
    r = service.approve(db, _load(db, reading_id), staff=staff.actor, can_correct=staff.can(P.READINGS_CORRECT_VALUE),
                        approved_value=body.approved_value, note=body.note, request=request)
    return _detail(db, r, staff)


@router.post("/{reading_id}/needs-correction", response_model=AdminReadingDetailOut)
def needs_correction(reading_id: int, body: CloseIn, request: Request, db: DB,
                     staff: StaffCtx = require(P.READINGS_REVIEW)) -> AdminReadingDetailOut:
    r = service.needs_correction(db, _load(db, reading_id), staff=staff.actor, reason_code=body.reason_code,
                                 note=body.note, request=request)
    return _detail(db, r, staff)


@router.post("/{reading_id}/reject", response_model=AdminReadingDetailOut)
def reject(reading_id: int, body: CloseIn, request: Request, db: DB,
           staff: StaffCtx = require(P.READINGS_REVIEW)) -> AdminReadingDetailOut:
    r = service.reject(db, _load(db, reading_id), staff=staff.actor, reason_code=body.reason_code, note=body.note,
                       request=request)
    return _detail(db, r, staff)
