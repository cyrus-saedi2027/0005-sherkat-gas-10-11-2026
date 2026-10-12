"""Finance unit (R21, R40): redemption approvals, payouts, suspicious behaviour."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request
from pydantic import BaseModel, Field
from sqlalchemy import func, select

from app.core.deps import DB, StaffCtx, require
from app.core.errors import AppError
from app.core.pagination import Page, PageParams, page_params
from app.core.rbac import P
from app.modules.points import service as points
from app.modules.points.models import PointsLedger
from app.modules.referrals.models import Referral
from app.modules.staff.models import StaffUser
from app.modules.store import service
from app.modules.store.models import Redemption
from app.modules.store.schemas import AdminRedemptionOut, RedemptionOut
from app.modules.subscribers.models import Subscriber
from app.modules.users.models import User

router = APIRouter(prefix="/finance", tags=["admin:finance"])


class ReviewIn(BaseModel):
    approve: bool
    note: str | None = Field(default=None, max_length=500)


class FulfillIn(BaseModel):
    payment_ref: str | None = Field(default=None, max_length=80)
    note: str | None = Field(default=None, max_length=500)


def _out(db, r: Redemption) -> AdminRedemptionOut:
    u = db.get(User, r.user_id)
    sub = db.get(Subscriber, u.subscriber_id) if u else None
    rev = db.get(StaffUser, r.reviewed_by) if r.reviewed_by else None
    name = " ".join(x for x in ((u.first_name, u.last_name) if u else ()) if x) or (sub.full_name if sub else None)
    return AdminRedemptionOut(**RedemptionOut.model_validate(r, from_attributes=True).model_dump(), user_id=r.user_id,
                              user_name=name, subscription_no=sub.subscription_no if sub else None,
                              iban_masked=service.masked_iban(r), fraud_signals=r.fraud_signals or {},
                              available_balance=points.balance(db, r.user_id).available,
                              reviewed_by_name=rev.full_name if rev else None)


@router.get("/redemptions", response_model=Page[AdminRedemptionOut])
def queue(db: DB, p: PageParams = Depends(page_params),
          status: Annotated[str | None, Query(pattern="^(submitted|approved|rejected|fulfilled|cancelled)$")] = "submitted",
          kind: Annotated[str | None, Query(pattern="^(product|discount|cash|donation)$")] = None,
          flagged_only: bool = False, _s: StaffCtx = require(P.REDEMPTIONS_VIEW)) -> Page[AdminRedemptionOut]:
    stmt = select(Redemption).order_by(Redemption.id.asc() if status == "submitted" else Redemption.id.desc())
    if status:
        stmt = stmt.where(Redemption.status == status)
    if kind:
        stmt = stmt.where(Redemption.kind == kind)
    rows = list(db.scalars(stmt).all()) if flagged_only else None
    if rows is not None:
        rows = [r for r in rows if r.fraud_signals]
        total, rows = len(rows), rows[p.offset:p.offset + p.size]
    else:
        total = int(db.scalar(select(func.count()).select_from(stmt.order_by(None).subquery())) or 0)
        rows = list(db.scalars(stmt.limit(p.size).offset(p.offset)).all())
    return Page(items=[_out(db, r) for r in rows], total=total, page=p.page, size=p.size)


@router.get("/summary")
def summary(db: DB, _s: StaffCtx = require(P.REDEMPTIONS_VIEW)) -> dict[str, int]:
    by = dict(db.execute(select(Redemption.status, func.count()).group_by(Redemption.status)).all())
    paid = db.scalar(select(func.coalesce(func.sum(Redemption.rial_value), 0)).where(Redemption.status == "fulfilled",
                                                                                      Redemption.kind == "cash")) or 0
    suspended = db.scalar(select(func.coalesce(func.sum(PointsLedger.amount), 0)).where(PointsLedger.status == "suspended")) or 0
    sus_ref = db.scalar(select(func.count()).where(Referral.status == "suspicious")) or 0
    return {"submitted": int(by.get("submitted", 0)), "approved": int(by.get("approved", 0)),
            "fulfilled": int(by.get("fulfilled", 0)), "rejected": int(by.get("rejected", 0)),
            "cash_paid_rial": int(paid), "suspended_points": int(suspended), "suspicious_referrals": int(sus_ref)}


def _load(db, rid: int) -> Redemption:
    r = db.get(Redemption, rid)
    if r is None:
        raise AppError("not_found", "درخواست پیدا نشد.", 404)
    return r


@router.post("/redemptions/{redemption_id}/review", response_model=AdminRedemptionOut)
def review(redemption_id: int, body: ReviewIn, request: Request, db: DB,
           staff: StaffCtx = require(P.REDEMPTIONS_REVIEW)) -> AdminRedemptionOut:
    return _out(db, service.review(db, _load(db, redemption_id), approve=body.approve, note=body.note, staff=staff.actor,
                                   request=request))


@router.post("/redemptions/{redemption_id}/fulfill", response_model=AdminRedemptionOut)
def fulfill(redemption_id: int, body: FulfillIn, request: Request, db: DB,
            staff: StaffCtx = require(P.REDEMPTIONS_FULFILL)) -> AdminRedemptionOut:
    return _out(db, service.fulfill(db, _load(db, redemption_id), payment_ref=body.payment_ref, note=body.note,
                                    staff=staff.actor, request=request))
