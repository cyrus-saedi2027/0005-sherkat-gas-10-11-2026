from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core import clock, crypto
from app.core.deps import StaffCtx
from app.core.normalize import mask_mobile
from app.core.rbac import P
from app.modules.cases import service
from app.modules.cases.models import (
    Case,
    CaseCall,
    CaseChecklist,
    CaseEstimate,
    CaseEvent,
    CasePhoto,
    CaseVisit,
)
from app.modules.cases.schemas import (
    CallOut,
    CaseDetail,
    CaseEventOut,
    CaseOut,
    ChecklistOut,
    EstimateOut,
    PhotoOut,
    UserCaseOut,
    VisitOut,
)
from app.modules.files import service as files
from app.modules.regions.models import Region
from app.modules.staff.models import StaffUser
from app.modules.subscribers.models import Subscriber


def staff_names(db: Session, ids: set[int]) -> dict[int, str]:
    ids = {i for i in ids if i}
    if not ids:
        return {}
    return dict(db.execute(select(StaffUser.id, StaffUser.full_name).where(StaffUser.id.in_(ids))).all())


def next_visit(db: Session, case_id: int) -> CaseVisit | None:
    return db.scalar(select(CaseVisit).where(CaseVisit.case_id == case_id, CaseVisit.status == "scheduled",
                                             CaseVisit.scheduled_end >= clock.now()).order_by(CaseVisit.scheduled_start))


def case_out(db: Session, c: Case, sub: Subscriber | None = None, region: Region | None = None,
             names: dict[int, str] | None = None) -> CaseOut:
    sub = sub or db.get(Subscriber, c.subscriber_id)
    region = region if region is not None else (db.get(Region, c.region_id) if c.region_id else None)
    names = names if names is not None else staff_names(db, {c.ambassador_id or 0})
    nv = next_visit(db, c.id)
    return CaseOut(
        id=c.id, status=c.status, tier=c.tier, suggested_tier=c.suggested_tier, needs_field_visit=c.needs_field_visit,
        priority=c.priority, opened_reason=c.opened_reason, user_id=c.user_id, subscriber_id=c.subscriber_id,
        subscription_no=sub.subscription_no if sub else "", subscriber_name=sub.full_name if sub else None,
        mobile_masked=mask_mobile(crypto.decrypt(sub.mobile_enc)) if sub else "—", region_id=c.region_id,
        region_name=region.name if region else None, ambassador_id=c.ambassador_id,
        ambassador_name=names.get(c.ambassador_id or 0), assignment_method=c.assignment_method, assigned_at=c.assigned_at,
        next_visit_at=nv.scheduled_start if nv else None, created_at=c.created_at, updated_at=c.updated_at,
        completed_at=c.completed_at,
    )


def visit_out(v: CaseVisit, names: dict[int, str], sub: Subscriber | None = None) -> VisitOut:
    return VisitOut(id=v.id, case_id=v.case_id, ambassador_id=v.ambassador_id, ambassador_name=names.get(v.ambassador_id),
                    scheduled_start=v.scheduled_start, scheduled_end=v.scheduled_end, status=v.status, note=v.note,
                    subscriber_name=sub.full_name if sub else None, address=sub.address if sub else None)


def photo_out(p: CasePhoto) -> PhotoOut:
    return PhotoOut(id=p.id, phase=p.phase, caption=p.caption, url=files.url(p.file_id), thumb_url=files.url(p.file_id, "thumb"),
                    created_at=p.created_at)


def estimate_out(e: CaseEstimate) -> EstimateOut:
    return EstimateOut.model_validate(e, from_attributes=True)


def allowed_actions(c: Case, staff: StaffCtx) -> list[str]:
    acts: list[str] = []
    work = staff.can(P.CASES_WORK) or "super_admin" in staff.roles
    if work:
        for action, froms in service.ALLOWED_FROM.items():
            if action in ("final_approve", "return_to_ambassador"):
                continue
            if c.status in froms:
                acts.append(action)
        if c.status in ("contacted", "evaluated", "visit_scheduled", "visited"):
            acts.append("checklist")
        if c.status not in service.CLOSED_STATUSES:
            acts.append("photo")
    if staff.can(P.CASES_FINAL_APPROVE) and c.status == "pending_final_approval":
        acts += ["final_approve", "return_to_ambassador"]
    if staff.can(P.CASES_ASSIGN) and c.status not in service.CLOSED_STATUSES:
        acts += ["reassign", "close"]
    return sorted(set(acts))


def case_detail(db: Session, c: Case, staff: StaffCtx) -> CaseDetail:
    sub = db.get(Subscriber, c.subscriber_id)
    calls = db.scalars(select(CaseCall).where(CaseCall.case_id == c.id).order_by(CaseCall.id.desc())).all()
    visits = db.scalars(select(CaseVisit).where(CaseVisit.case_id == c.id).order_by(CaseVisit.scheduled_start.desc())).all()
    photos = db.scalars(select(CasePhoto).where(CasePhoto.case_id == c.id).order_by(CasePhoto.id)).all()
    ests = db.scalars(select(CaseEstimate).where(CaseEstimate.case_id == c.id).order_by(CaseEstimate.id.desc())).all()
    evs = db.scalars(select(CaseEvent).where(CaseEvent.case_id == c.id).order_by(CaseEvent.id)).all()
    ch = db.scalar(select(CaseChecklist).where(CaseChecklist.case_id == c.id))
    names = staff_names(db, {c.ambassador_id or 0} | {v.ambassador_id for v in visits} |
                        {e.actor_id or 0 for e in evs if e.actor_type == "staff"})
    base = case_out(db, c, sub, None, names)
    return CaseDetail(
        **base.model_dump(), address=sub.address if sub else None, tier_reason=c.tier_reason, executed=c.executed,
        closed_reason=c.closed_reason,
        checklist=ChecklistOut.model_validate(ch, from_attributes=True) if ch else None,
        calls=[CallOut.model_validate(x, from_attributes=True) for x in calls],
        visits=[visit_out(v, names, sub) for v in visits], photos=[photo_out(p) for p in photos],
        estimates=[estimate_out(e) for e in ests],
        events=[CaseEventOut(**{**CaseEventOut.model_validate(e, from_attributes=True).model_dump(),
                                "actor_name": names.get(e.actor_id or 0) if e.actor_type == "staff" else
                                ("مشترک" if e.actor_type == "user" else "سامانه")}) for e in evs],
        baseline_annual_m3=sub.baseline_annual_m3 if sub else None, allowed_actions=allowed_actions(c, staff),
    )


def user_case(db: Session, c: Case) -> UserCaseOut:
    names = staff_names(db, {c.ambassador_id or 0})
    nv = next_visit(db, c.id)
    est = db.scalar(select(CaseEstimate).where(CaseEstimate.case_id == c.id, CaseEstimate.status != "superseded")
                    .order_by(CaseEstimate.id.desc()))
    photos = db.scalars(select(CasePhoto).where(CasePhoto.case_id == c.id).order_by(CasePhoto.id)).all()
    evs = db.scalars(select(CaseEvent).where(CaseEvent.case_id == c.id, CaseEvent.to_status.is_not(None))
                     .order_by(CaseEvent.id)).all()
    # The subscriber sees milestones only — no staff names/ids, no internal notes.
    timeline = [CaseEventOut(id=e.id, actor_type=e.actor_type, actor_id=None, actor_name=None, action=e.action,
                             from_status=e.from_status, to_status=e.to_status, note=None, created_at=e.created_at)
                for e in evs if e.from_status != e.to_status]
    amb = names.get(c.ambassador_id or 0)
    return UserCaseOut(id=c.id, status=c.status, tier=c.tier, needs_field_visit=c.needs_field_visit,
                       ambassador_name=(amb.split(" ")[0] + " (سفیر طرح)") if amb else None,
                       next_visit=visit_out(nv, names) if nv else None, estimate=estimate_out(est) if est else None,
                       photos=[photo_out(p) for p in photos], timeline=timeline, created_at=c.created_at,
                       completed_at=c.completed_at)
