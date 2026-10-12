from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy import select

from app.core import audit
from app.core.deps import DB, StaffCtx, require
from app.core.errors import AppError
from app.core.pagination import PageParams, page_params, paginate
from app.core.rbac import P
from app.modules.points import service
from app.modules.points.models import PointsLedger, PointsRule
from app.modules.points.router_app import ledger_out
from app.modules.points.schemas import (
    AdjustIn,
    BalanceOut,
    LedgerOut,
    LedgerPage,
    RuleOut,
    RuleUpdate,
    SuspendIn,
    UnsuspendIn,
)

router = APIRouter(prefix="/points", tags=["admin:points"])


@router.get("/rules", response_model=list[RuleOut])
def list_rules(db: DB, _s: StaffCtx = require(P.POINTS_VIEW)) -> list[RuleOut]:
    service.seed_rules(db)
    rows = db.scalars(select(PointsRule).order_by(PointsRule.id)).all()
    return [RuleOut.model_validate(r, from_attributes=True) for r in rows]


@router.put("/rules/{event_type}", response_model=RuleOut)
def update_rule(event_type: str, body: RuleUpdate, request: Request, db: DB,
                staff: StaffCtx = require(P.POINTS_RULES_EDIT)) -> RuleOut:
    service.seed_rules(db)
    r = db.scalar(select(PointsRule).where(PointsRule.event_type == event_type))
    if r is None:
        raise AppError("not_found", "قانون امتیاز پیدا نشد.", 404)
    before = audit.snapshot(r, ["points", "is_active", "monthly_cap_points", "title_fa"])
    r.points, r.is_active, r.monthly_cap_points = body.points, body.is_active, body.monthly_cap_points
    if body.title_fa:
        r.title_fa = body.title_fa
    r.updated_by = staff.id
    audit.record(db, staff.actor, "points.rule_update", "points_rule", event_type, before,
                 audit.snapshot(r, ["points", "is_active", "monthly_cap_points", "title_fa"]), request)
    return RuleOut.model_validate(r, from_attributes=True)


@router.get("/ledger", response_model=LedgerPage)
def ledger(db: DB, p: PageParams = Depends(page_params), user_id: int | None = None,
           status: Annotated[str | None, Query(pattern="^(pending|available|suspended|reversed)$")] = None,
           event_type: str | None = None, _s: StaffCtx = require(P.POINTS_VIEW)) -> LedgerPage:
    stmt = select(PointsLedger).order_by(PointsLedger.id.desc())
    if user_id:
        stmt = stmt.where(PointsLedger.user_id == user_id)
    if status:
        stmt = stmt.where(PointsLedger.status == status)
    if event_type:
        stmt = stmt.where(PointsLedger.event_type == event_type)
    rows, total = paginate(db, stmt, p)
    return LedgerPage(items=[ledger_out(db, e) for e in rows], total=total, page=p.page, size=p.size)


@router.get("/users/{user_id}/balance", response_model=BalanceOut)
def user_balance(user_id: int, db: DB, _s: StaffCtx = require(P.POINTS_VIEW)) -> BalanceOut:
    from app.core import settings_registry as reg

    b = service.balance(db, user_id)
    rate = reg.get_int(db, "finance.point_rial_rate")
    return BalanceOut(available=b.available, pending=b.pending, suspended=b.suspended, total=b.total,
                      rial_rate=rate, available_rial=b.available * rate, next_release_at=None)


@router.post("/adjust", response_model=LedgerOut)
def adjust(body: AdjustIn, db: DB, staff: StaffCtx = require(P.POINTS_ADJUST)) -> LedgerOut:
    from app.modules.users.models import User

    if db.get(User, body.user_id) is None:
        raise AppError("not_found", "کاربر پیدا نشد.", 404)
    return ledger_out(db, service.adjust(db, user_id=body.user_id, amount=body.amount, reason=body.reason, staff=staff.actor))


@router.post("/ledger/{entry_id}/suspend", response_model=LedgerOut)
def suspend(entry_id: int, body: SuspendIn, db: DB, staff: StaffCtx = require(P.POINTS_SUSPEND)) -> LedgerOut:
    return ledger_out(db, service.suspend(db, entry_id, body.reason, staff.actor))


@router.post("/ledger/{entry_id}/unsuspend", response_model=LedgerOut)
def unsuspend(entry_id: int, body: UnsuspendIn, db: DB, staff: StaffCtx = require(P.POINTS_SUSPEND)) -> LedgerOut:
    return ledger_out(db, service.unsuspend(db, entry_id, staff.actor, reverse=body.reverse))
