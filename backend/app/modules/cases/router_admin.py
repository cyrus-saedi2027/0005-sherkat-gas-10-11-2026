from __future__ import annotations

from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, Query, Request, UploadFile
from sqlalchemy import func, or_, select

from app.core.deps import DB, StaffCtx, require_any
from app.core.errors import AppError
from app.core.normalize import normalize_subscription, normalize_text
from app.core.pagination import Page, PageParams, page_params
from app.core.rbac import P
from app.modules.cases import presenter, service
from app.modules.cases.models import Case, CaseVisit
from app.modules.cases.schemas import (
    AssignIn,
    CallIn,
    CallOut,
    CaseDetail,
    CaseOut,
    ChecklistIn,
    CloseIn,
    EstimateIn,
    EvaluateIn,
    NoteIn,
    OpenCaseIn,
    ReasonIn,
    VisitDoneIn,
    VisitIn,
    VisitOut,
)
from app.modules.regions.models import Region
from app.modules.regions.service import descendants
from app.modules.subscribers.models import Subscriber
from app.modules.users.models import User

router = APIRouter(prefix="/cases", tags=["admin:cases"])
VIEW = require_any(P.CASES_VIEW_ALL, P.CASES_VIEW_OWN)


def _need(staff: StaffCtx, *perms: P) -> None:
    if not any(staff.can(p) for p in perms):
        raise AppError("forbidden", "شما اجازهٔ انجام این عملیات را ندارید.", 403)


@router.get("", response_model=Page[CaseOut])
def list_cases(db: DB, p: PageParams = Depends(page_params), staff: StaffCtx = VIEW,
               status: Annotated[str | None, Query(max_length=24)] = None,
               tier: Annotated[str | None, Query(pattern="^(no_cost|low_cost|high_cost)$")] = None,
               region_id: int | None = None, ambassador_id: int | None = None, unassigned: bool = False,
               q: Annotated[str | None, Query(max_length=40)] = None, open_only: bool = False) -> Page[CaseOut]:
    stmt = (select(Case, Subscriber, Region).join(Subscriber, Subscriber.id == Case.subscriber_id)
            .outerjoin(Region, Region.id == Case.region_id))
    if not staff.can(P.CASES_VIEW_ALL):
        stmt = stmt.where(Case.ambassador_id == staff.id)
    if status:
        stmt = stmt.where(Case.status == status)
    if open_only:
        stmt = stmt.where(Case.status.in_(service.OPEN_STATUSES))
    if tier:
        stmt = stmt.where(Case.tier == tier)
    if region_id:
        stmt = stmt.where(Case.region_id.in_(descendants(db, region_id)))
    if ambassador_id:
        stmt = stmt.where(Case.ambassador_id == ambassador_id)
    if unassigned:
        stmt = stmt.where(Case.ambassador_id.is_(None))
    if q:
        conds = [Subscriber.full_name.ilike(f"%{normalize_text(q)}%")]
        if (sn := normalize_subscription(q)):
            conds.append(Subscriber.subscription_no.startswith(sn))
        if q.isdigit():
            conds.append(Case.id == int(q))
        stmt = stmt.where(or_(*conds))
    prio = {"high": 0, "normal": 1, "low": 2}
    stmt = stmt.order_by(Case.updated_at.desc())
    total = int(db.scalar(select(func.count()).select_from(stmt.order_by(None).subquery())) or 0)
    rows = db.execute(stmt.limit(p.size).offset(p.offset)).all()
    names = presenter.staff_names(db, {c.ambassador_id or 0 for c, _, _ in rows})
    items = [presenter.case_out(db, c, s, r, names) for c, s, r in rows]
    items.sort(key=lambda x: prio.get(x.priority, 1))  # stable: keeps recency within a priority
    return Page(items=items, total=total, page=p.page, size=p.size)


@router.get("/stats")
def stats(db: DB, staff: StaffCtx = VIEW) -> dict[str, dict[str, int]]:
    base = select(Case.status, func.count()).group_by(Case.status)
    tier_q = select(Case.tier, func.count()).where(Case.tier.is_not(None)).group_by(Case.tier)
    if not staff.can(P.CASES_VIEW_ALL):
        base, tier_q = base.where(Case.ambassador_id == staff.id), tier_q.where(Case.ambassador_id == staff.id)
    unassigned = select(func.count()).where(Case.ambassador_id.is_(None), Case.status == "new")
    return {"by_status": {k: int(v) for k, v in db.execute(base).all()},
            "by_tier": {k: int(v) for k, v in db.execute(tier_q).all()},
            "queues": {"unassigned": int(db.scalar(unassigned) or 0) if staff.can(P.CASES_VIEW_ALL) else 0}}


@router.get("/calendar", response_model=list[VisitOut])
def calendar(db: DB, date_from: datetime, date_to: datetime, ambassador_id: int | None = None,
             staff: StaffCtx = VIEW) -> list[VisitOut]:
    """Ambassador calendar (R30). Ambassadors only see their own visits."""
    if (date_to - date_from).days > 62:
        raise AppError("validation_error", "بازهٔ تقویم حداکثر دو ماه است.", 422)
    stmt = select(CaseVisit, Subscriber).join(Case, Case.id == CaseVisit.case_id).join(Subscriber, Subscriber.id == Case.subscriber_id) \
        .where(CaseVisit.scheduled_start < date_to, CaseVisit.scheduled_end > date_from, CaseVisit.status != "cancelled")
    if not staff.can(P.CASES_VIEW_ALL):
        stmt = stmt.where(CaseVisit.ambassador_id == staff.id)
    elif ambassador_id:
        stmt = stmt.where(CaseVisit.ambassador_id == ambassador_id)
    rows = db.execute(stmt.order_by(CaseVisit.scheduled_start).limit(500)).all()
    names = presenter.staff_names(db, {v.ambassador_id for v, _ in rows})
    return [presenter.visit_out(v, names, s) for v, s in rows]


@router.get("/workload")
def workload(db: DB, _s: StaffCtx = require_any(P.CASES_ASSIGN)) -> list[dict]:
    from app.modules.staff.models import StaffUser

    out = []
    for s in db.scalars(select(StaffUser).where(StaffUser.is_active.is_(True))).all():
        if "ambassador" in (s.roles or []):
            out.append({"id": s.id, "full_name": s.full_name, "region_ids": s.service_region_ids or [],
                        "workload": service.workload(db, s.id), "last_assigned_at": s.last_assigned_at})
    return sorted(out, key=lambda x: x["workload"])


@router.post("", response_model=CaseDetail, status_code=201)
def open_manual(body: OpenCaseIn, request: Request, db: DB, staff: StaffCtx = require_any(P.CASES_ASSIGN)) -> CaseDetail:
    u = db.get(User, body.user_id)
    if u is None:
        raise AppError("not_found", "کاربر پیدا نشد.", 404)
    if service.open_case_for(db, u.id):
        raise AppError("case_exists", "این کاربر پروندهٔ باز دارد.", 409)
    c = service.open_case(db, user=u, reason="manual", actor=staff.actor, priority=body.priority)
    return presenter.case_detail(db, c, staff)


@router.get("/{case_id}", response_model=CaseDetail)
def detail(case_id: int, db: DB, staff: StaffCtx = VIEW) -> CaseDetail:
    return presenter.case_detail(db, service.get_case(db, case_id, staff), staff)


@router.post("/{case_id}/assign", response_model=CaseDetail)
def assign(case_id: int, body: AssignIn, request: Request, db: DB, staff: StaffCtx = require_any(P.CASES_ASSIGN)) -> CaseDetail:
    c = service.reassign(db, service.get_case(db, case_id, staff), body.ambassador_id, staff.actor, request)
    return presenter.case_detail(db, c, staff)


@router.post("/{case_id}/auto-assign", response_model=CaseDetail)
def auto_assign(case_id: int, db: DB, staff: StaffCtx = require_any(P.CASES_ASSIGN)) -> CaseDetail:
    c = service.get_case(db, case_id, staff)
    if c.status != "new":
        raise AppError("bad_state", "پرونده قبلاً ارجاع شده است.", 409)
    if service.auto_assign(db, c) is None:
        raise AppError("no_ambassador", "سفیر فعالی برای ارجاع پیدا نشد.", 409)
    return presenter.case_detail(db, c, staff)


def _work(db, case_id: int, staff: StaffCtx) -> Case:
    _need(staff, P.CASES_WORK)
    return service.get_case(db, case_id, staff, for_work=True)


@router.post("/{case_id}/calls", response_model=CallOut, status_code=201)
def log_call(case_id: int, body: CallIn, request: Request, db: DB, staff: StaffCtx = VIEW) -> CallOut:
    call = service.log_call(db, _work(db, case_id, staff), staff, body.outcome, body.note, body.next_call_at, request)
    return CallOut.model_validate(call, from_attributes=True)


@router.put("/{case_id}/checklist", response_model=CaseDetail)
def checklist(case_id: int, body: ChecklistIn, db: DB, staff: StaffCtx = VIEW) -> CaseDetail:
    c = _work(db, case_id, staff)
    data = body.model_dump()
    data["heating_equipment"] = [e.model_dump() for e in body.heating_equipment]
    service.save_checklist(db, c, staff, data)
    return presenter.case_detail(db, c, staff)


@router.post("/{case_id}/evaluate", response_model=CaseDetail)
def evaluate(case_id: int, body: EvaluateIn, request: Request, db: DB, staff: StaffCtx = VIEW) -> CaseDetail:
    c = service.evaluate(db, _work(db, case_id, staff), staff, tier=body.tier, needs_field_visit=body.needs_field_visit,
                         reason=body.reason, request=request)
    return presenter.case_detail(db, c, staff)


@router.post("/{case_id}/visits", response_model=CaseDetail)
def schedule(case_id: int, body: VisitIn, request: Request, db: DB, staff: StaffCtx = VIEW) -> CaseDetail:
    c = _work(db, case_id, staff)
    service.schedule_visit(db, c, staff, body.start, body.end, body.note, request)
    return presenter.case_detail(db, c, staff)


@router.post("/{case_id}/visit-done", response_model=CaseDetail)
def visit_done(case_id: int, body: VisitDoneIn, request: Request, db: DB, staff: StaffCtx = VIEW) -> CaseDetail:
    c = service.visit_done(db, _work(db, case_id, staff), staff, body.outcome, body.note, request)
    return presenter.case_detail(db, c, staff)


@router.post("/{case_id}/photos", response_model=CaseDetail)
async def photo(case_id: int, db: DB, phase: Annotated[str, Form(pattern="^(before|after)$")],
                file: Annotated[UploadFile, File()], caption: Annotated[str | None, Form(max_length=300)] = None,
                staff: StaffCtx = VIEW) -> CaseDetail:
    c = _work(db, case_id, staff)
    raw = await file.read(20 * 1024 * 1024 + 1)
    service.add_photo(db, c, staff, raw, phase, caption, file.filename)
    return presenter.case_detail(db, c, staff)


@router.post("/{case_id}/estimates", response_model=CaseDetail)
def estimate(case_id: int, body: EstimateIn, request: Request, db: DB, staff: StaffCtx = VIEW) -> CaseDetail:
    c = _work(db, case_id, staff)
    service.create_estimate(db, c, staff, [i.model_dump() for i in body.items], body.note, request)
    return presenter.case_detail(db, c, staff)


@router.post("/{case_id}/executed", response_model=CaseDetail)
def executed(case_id: int, body: NoteIn, request: Request, db: DB, staff: StaffCtx = VIEW) -> CaseDetail:
    c = service.mark_executed(db, _work(db, case_id, staff), staff, body.note, request)
    return presenter.case_detail(db, c, staff)


@router.post("/{case_id}/submit-final", response_model=CaseDetail)
def submit_final(case_id: int, body: NoteIn, request: Request, db: DB, staff: StaffCtx = VIEW) -> CaseDetail:
    c = service.submit_for_final(db, _work(db, case_id, staff), staff, body.note, request)
    return presenter.case_detail(db, c, staff)


@router.post("/{case_id}/final-approve", response_model=CaseDetail)
def final_approve(case_id: int, body: NoteIn, request: Request, db: DB,
                  staff: StaffCtx = require_any(P.CASES_FINAL_APPROVE)) -> CaseDetail:
    c = service.final_approve(db, service.get_case(db, case_id, staff), staff, body.note, request)
    return presenter.case_detail(db, c, staff)


@router.post("/{case_id}/return", response_model=CaseDetail)
def return_case(case_id: int, body: ReasonIn, request: Request, db: DB,
                staff: StaffCtx = require_any(P.CASES_FINAL_APPROVE)) -> CaseDetail:
    c = service.return_to_ambassador(db, service.get_case(db, case_id, staff), staff, body.reason, request)
    return presenter.case_detail(db, c, staff)


@router.post("/{case_id}/close", response_model=CaseDetail)
def close(case_id: int, body: CloseIn, request: Request, db: DB, staff: StaffCtx = require_any(P.CASES_ASSIGN)) -> CaseDetail:
    c = service.close(db, service.get_case(db, case_id, staff), staff, body.status, body.reason, request)
    return presenter.case_detail(db, c, staff)


