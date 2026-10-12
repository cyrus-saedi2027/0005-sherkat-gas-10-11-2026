"""Technical evaluation & ambassador workflow (R14–R19, R30, R38, R43).

State machine (ARCHITECTURE §3.5):

  new → assigned → contacted → evaluated ─┬─(no visit)──────────────▶ pending_final_approval
                                          └─ visit_scheduled → visited ─┬─ share>0: awaiting_consent → consent_given → in_execution ─▶ pending_final_approval
                                                                        └─ share=0: in_execution ──────────────────────────────────▶ pending_final_approval
  pending_final_approval → completed (technician)      any open → cancelled / closed_no_action
  awaiting_consent → consent_declined (user) → closed_no_action, or a new estimate re-opens consent
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

from fastapi import Request
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core import audit, clock, events, jalali
from app.core import settings_registry as reg
from app.core.deps import StaffCtx
from app.core.errors import AppError
from app.core.rbac import P
from app.modules.cases.models import (
    Case,
    CaseCall,
    CaseChecklist,
    CaseEstimate,
    CaseEvent,
    CasePhoto,
    CaseVisit,
)
from app.modules.notifications.service import notify
from app.modules.regions.service import ancestors
from app.modules.staff.models import StaffUser
from app.modules.subscribers.models import Subscriber
from app.modules.users.models import User

OPEN_STATUSES = ("new", "assigned", "contacted", "evaluated", "visit_scheduled", "visited", "awaiting_consent",
                 "consent_given", "in_execution", "pending_final_approval")
CLOSED_STATUSES = ("completed", "closed_no_action", "cancelled", "consent_declined")
TIERS = ("no_cost", "low_cost", "high_cost")
TIER_FA = {"no_cost": "بدون‌هزینه", "low_cost": "کم‌هزینه", "high_cost": "پرهزینه"}

# Which transitions each action may start from.
ALLOWED_FROM: dict[str, tuple[str, ...]] = {
    "call": ("assigned", "contacted", "evaluated", "visit_scheduled", "visited", "awaiting_consent", "consent_given", "in_execution"),
    "evaluate": ("contacted", "evaluated"),
    "schedule_visit": ("evaluated", "visit_scheduled", "visited"),
    "visit_done": ("visit_scheduled",),
    "estimate": ("visited", "awaiting_consent", "consent_declined", "consent_given"),
    "executed": ("in_execution", "consent_given"),
    "submit_final": ("evaluated", "visited", "in_execution"),
    "final_approve": ("pending_final_approval",),
    "return_to_ambassador": ("pending_final_approval",),
}


# ───────────────────────── helpers ─────────────────────────

def _event(db: Session, c: Case, actor: audit.Actor, action: str, to: str | None, note: str | None = None) -> None:
    db.add(CaseEvent(case_id=c.id, actor_type=actor.type, actor_id=actor.id, action=action, from_status=c.status,
                     to_status=to, note=note))


def _move(db: Session, c: Case, actor: audit.Actor, action: str, to: str, note: str | None = None,
          request: Request | None = None) -> None:
    _event(db, c, actor, action, to, note)
    before = c.status
    c.status = to
    audit.record(db, actor, f"case.{action}", "case", c.id, {"status": before}, {"status": to, "note": note}, request)


def _require(c: Case, action: str) -> None:
    if c.status not in ALLOWED_FROM[action]:
        raise AppError("bad_state", "این عملیات در وضعیت فعلی پرونده مجاز نیست.", 409, {"status": c.status})


def get_case(db: Session, case_id: int, staff: StaffCtx | None = None, *, for_work: bool = False) -> Case:
    c = db.get(Case, case_id)
    if c is None:
        raise AppError("not_found", "پرونده پیدا نشد.", 404)
    # Row-level rule: an ambassador only sees and works their own cases.
    if staff is not None and not staff.can(P.CASES_VIEW_ALL) and c.ambassador_id != staff.id:
        raise AppError("not_found", "پرونده پیدا نشد.", 404)
    if for_work and staff is not None and not staff.can(P.CASES_WORK) and "super_admin" not in staff.roles:
        raise AppError("forbidden", "شما اجازهٔ انجام این عملیات را ندارید.", 403)
    return c


def open_case_for(db: Session, user_id: int) -> Case | None:
    return db.scalar(select(Case).where(Case.user_id == user_id, Case.status.in_(OPEN_STATUSES)))


# ───────────────────────── opening & assignment ─────────────────────────

def open_case(db: Session, *, user: User, reason: str, reading_id: int | None = None,
              actor: audit.Actor = audit.SYSTEM, priority: str = "normal") -> Case:
    existing = open_case_for(db, user.id)
    if existing is not None:
        return existing
    sub = db.get(Subscriber, user.subscriber_id)
    c = Case(user_id=user.id, subscriber_id=user.subscriber_id, region_id=sub.region_id if sub else None,
             opened_reason=reason, opened_by_reading_id=reading_id, priority=priority)
    db.add(c)
    db.flush()
    _event(db, c, actor, "opened", "new", reason)
    audit.record(db, actor, "case.open", "case", c.id, None, {"user_id": user.id, "reason": reason})
    auto_assign(db, c)
    return c


def workload(db: Session, ambassador_id: int) -> int:
    now = clock.now()
    open_cases = db.scalar(select(func.count()).where(Case.ambassador_id == ambassador_id, Case.status.in_(OPEN_STATUSES))) or 0
    visits = db.scalar(select(func.count()).where(CaseVisit.ambassador_id == ambassador_id, CaseVisit.status == "scheduled",
                                                  CaseVisit.scheduled_start >= now,
                                                  CaseVisit.scheduled_start < now + timedelta(days=7))) or 0
    return int(open_cases) + int(visits)


def pick_ambassador(db: Session, region_id: int | None) -> StaffUser | None:
    """R38: by geographic area first, then lowest workload, then least recently assigned."""
    candidates = [s for s in db.scalars(select(StaffUser).where(StaffUser.is_active.is_(True))).all()
                  if "ambassador" in (s.roles or [])]
    if not candidates:
        return None
    region_chain = set(ancestors(db, region_id)) if region_id else set()
    local = [s for s in candidates if region_chain & set(s.service_region_ids or [])]
    pool = local or candidates
    epoch = datetime.min.replace(tzinfo=clock.now().tzinfo)
    return min(pool, key=lambda s: (workload(db, s.id), s.last_assigned_at or epoch, s.id))


def auto_assign(db: Session, c: Case) -> StaffUser | None:
    amb = pick_ambassador(db, c.region_id)
    if amb is None:
        return None  # stays "new" in the unassigned queue
    _assign(db, c, amb, "auto", audit.SYSTEM)
    return amb


def _assign(db: Session, c: Case, amb: StaffUser, method: str, actor: audit.Actor, request: Request | None = None) -> None:
    prev = c.ambassador_id
    c.ambassador_id, c.assignment_method, c.assigned_at = amb.id, method, clock.now()
    amb.last_assigned_at = clock.now()
    if c.status == "new":
        _move(db, c, actor, "assign", "assigned", f"{method}:{amb.full_name}", request)
    else:
        _event(db, c, actor, "reassign", c.status, f"{prev}→{amb.id}")
        audit.record(db, actor, "case.reassign", "case", c.id, {"ambassador_id": prev}, {"ambassador_id": amb.id}, request)
    notify(db, staff_id=amb.id, kind="case_assigned", title="پروندهٔ جدید به شما ارجاع شد",
           body=f"پروندهٔ شمارهٔ {jalali.to_fa_digits(str(c.id))} برای ارزیابی به شما سپرده شد.", data={"route": f"/cases/{c.id}"})


def reassign(db: Session, c: Case, ambassador_id: int, actor: audit.Actor, request: Request | None) -> Case:
    if c.status in CLOSED_STATUSES:
        raise AppError("bad_state", "پروندهٔ بسته را نمی‌توان ارجاع داد.", 409)
    amb = db.get(StaffUser, ambassador_id)
    if amb is None or not amb.is_active or "ambassador" not in (amb.roles or []):
        raise AppError("validation_error", "سفیر انتخاب‌شده معتبر نیست.", 422)
    _assign(db, c, amb, "manual", actor, request)
    return c


# ───────────────────────── ambassador work ─────────────────────────

def log_call(db: Session, c: Case, staff: StaffCtx, outcome: str, note: str | None, next_call_at: datetime | None,
             request: Request | None) -> CaseCall:
    """R16: the ambassador FIRST calls the subscriber; a reached call moves the case to «contacted»."""
    _require(c, "call")
    call = CaseCall(case_id=c.id, staff_id=staff.id, called_at=clock.now(), outcome=outcome, note=note, next_call_at=next_call_at)
    db.add(call)
    if outcome == "reached" and c.status == "assigned":
        _move(db, c, staff.actor, "contacted", "contacted", note, request)
    else:
        _event(db, c, staff.actor, f"call_{outcome}", c.status, note)
    db.flush()
    return call


def suggest_tier(ch: CaseChecklist) -> str:
    """Heuristic suggestion only — the ambassador decides (R16) and can override with a reason."""
    score = 0.0
    for eq in ch.heating_equipment or []:
        if eq.get("condition") == "poor" or (eq.get("age_years") or 0) >= 15:
            score += 2
        elif eq.get("condition") == "fair":
            score += 0.5
    score += {"blocked": 2, "needs_repair": 2}.get(ch.chimney_status or "", 0)
    score += {"none": 1, "partial": 0.5}.get(ch.insulation or "", 0)
    score += {"none": 1, "poor": 1}.get(ch.window_seals or "", 0)
    if (ch.built_area_m2 or ch.floor_area_m2 or 0) > 150:
        score += 1
    return "high_cost" if score >= 3 else "low_cost" if score >= 1 else "no_cost"


def save_checklist(db: Session, c: Case, staff: StaffCtx, data: dict[str, Any]) -> CaseChecklist:
    if c.status not in ("contacted", "evaluated", "visit_scheduled", "visited"):
        raise AppError("bad_state", "ابتدا تماس تلفنی با مشترک را ثبت کنید.", 409)
    ch = db.scalar(select(CaseChecklist).where(CaseChecklist.case_id == c.id))
    if ch is None:
        ch = CaseChecklist(case_id=c.id)
        db.add(ch)
    for k, v in data.items():
        setattr(ch, k, v)
    ch.completed_by = staff.id
    db.flush()
    c.suggested_tier = suggest_tier(ch)
    return ch


def evaluate(db: Session, c: Case, staff: StaffCtx, *, tier: str, needs_field_visit: bool, reason: str | None,
             request: Request | None) -> Case:
    """Route the case into one of the three groups (R14b, R16–R19)."""
    _require(c, "evaluate")
    if tier not in TIERS:
        raise AppError("validation_error", "گروه انتخاب‌شده معتبر نیست.", 422)
    ch = db.scalar(select(CaseChecklist).where(CaseChecklist.case_id == c.id))
    if ch is None:
        raise AppError("checklist_required", "ابتدا چک‌لیست ارزیابی را تکمیل کنید.", 409)
    if c.suggested_tier and tier != c.suggested_tier and not (reason or "").strip():
        raise AppError("validation_error", "گروه با پیشنهاد سامانه متفاوت است؛ دلیل را بنویسید.", 422,
                       {"fields": {"reason": "دلیل تغییر گروه را بنویسید."}})
    if tier == "no_cost":
        needs_field_visit = False  # no-cost group never needs a field visit (R17)
    c.tier, c.needs_field_visit, c.tier_reason = tier, needs_field_visit, (reason or "").strip() or None
    user = db.get(User, c.user_id)
    if user is not None:
        user.tier = tier
    _move(db, c, staff.actor, "evaluate", "evaluated", f"{TIER_FA[tier]}{' — بازدید لازم' if needs_field_visit else ''}", request)
    _deliver_education(db, c)
    return c


def _deliver_education(db: Session, c: Case) -> None:
    """R17–R19: the tier's user panel switches on and education/tips are sent by notification + SMS."""
    tier_fa = TIER_FA.get(c.tier or "", "")
    body = ("آموزش‌ها، مقالات و راهکارهای اصلاح الگوی مصرف ویژهٔ شما در بخش «آموزش» آماده است."
            if not c.needs_field_visit else
            "به‌زودی برای هماهنگی بازدید با شما تماس گرفته می‌شود. تا آن زمان راهکارهای بخش «آموزش» را ببینید.")
    notify(db, user_id=c.user_id, kind="tier_assigned", title=f"پروندهٔ شما در گروه «{tier_fa}» قرار گرفت",
           body=body, data={"route": "/learn", "tier": c.tier},
           sms_text="گازیار: پروندهٔ شما ارزیابی شد. راهکارهای صرفه‌جویی ویژهٔ شما در اپلیکیشن آماده است.")


def schedule_visit(db: Session, c: Case, staff: StaffCtx, start: datetime, end: datetime, note: str | None,
                   request: Request | None) -> CaseVisit:
    _require(c, "schedule_visit")
    if not c.needs_field_visit:
        raise AppError("bad_state", "برای این پرونده بازدید حضوری تعیین نشده است.", 409)
    if end <= start or start < clock.now() - timedelta(hours=1):
        raise AppError("validation_error", "بازهٔ زمانی بازدید معتبر نیست.", 422)
    amb_id = c.ambassador_id or staff.id
    clash = db.scalar(select(CaseVisit.id).where(CaseVisit.ambassador_id == amb_id, CaseVisit.status == "scheduled",
                                                 CaseVisit.scheduled_start < end, CaseVisit.scheduled_end > start))
    if clash:
        raise AppError("visit_conflict", "سفیر در این بازه بازدید دیگری دارد.", 409)
    for v in db.scalars(select(CaseVisit).where(CaseVisit.case_id == c.id, CaseVisit.status == "scheduled")):
        v.status = "cancelled"  # rescheduling replaces the previous slot
    v = CaseVisit(case_id=c.id, ambassador_id=amb_id, scheduled_start=start, scheduled_end=end, note=note)
    db.add(v)
    db.flush()
    _move(db, c, staff.actor, "schedule_visit", "visit_scheduled", note, request)
    notify(db, user_id=c.user_id, kind="visit_scheduled", title="زمان بازدید کارشناس تعیین شد",
           body=f"بازدید کارشناس در تاریخ {jalali.format_date(start)} ساعت {jalali.to_fa_digits(jalali.to_tehran(start).strftime('%H:%M'))} انجام می‌شود.",
           data={"route": "/case"}, sms_text=f"گازیار: بازدید کارشناس {jalali.format_date(start)} ساعت {jalali.to_tehran(start).strftime('%H:%M')}")
    return v


def visit_done(db: Session, c: Case, staff: StaffCtx, outcome: str, note: str | None, request: Request | None) -> Case:
    _require(c, "visit_done")
    v = db.scalar(select(CaseVisit).where(CaseVisit.case_id == c.id, CaseVisit.status == "scheduled"))
    if v is not None:
        v.status = "done" if outcome == "done" else "missed"
        v.note = note or v.note
    if outcome == "done":
        _move(db, c, staff.actor, "visit_done", "visited", note, request)
    else:
        _move(db, c, staff.actor, "visit_missed", "evaluated", note, request)  # back to scheduling
    return c


def add_photo(db: Session, c: Case, staff: StaffCtx, raw: bytes, phase: str, caption: str | None, name: str | None) -> CasePhoto:
    from app.modules.files import service as files

    if c.status in CLOSED_STATUSES:
        raise AppError("bad_state", "پرونده بسته است.", 409)
    if phase not in ("before", "after"):
        raise AppError("validation_error", "نوع تصویر معتبر نیست.", 422)
    f = files.save_image(db, raw, purpose=f"case_{phase}", owner_type="staff", owner_id=staff.id, original_name=name)
    p = CasePhoto(case_id=c.id, file_id=f.id, phase=phase, caption=(caption or "").strip()[:300] or None, uploaded_by=staff.id)
    db.add(p)
    _event(db, c, staff.actor, f"photo_{phase}", c.status, caption)
    db.flush()
    return p


def compute_split(db: Session, tier: str, total: int) -> tuple[int, int, int, int]:
    """(free_cap, share_pct, subscriber_share, program_share) — R06, R19."""
    free_cap = reg.get_int(db, "finance.free_cap_rial")
    if tier == "high_cost":
        pct = reg.get_int(db, "finance.copay_subscriber_pct")
        sub = round(total * pct / 100)
    else:
        pct = 0
        sub = max(0, total - free_cap)
    return free_cap, pct, sub, total - sub


def create_estimate(db: Session, c: Case, staff: StaffCtx, items: list[dict[str, Any]], note: str | None,
                    request: Request | None) -> CaseEstimate:
    _require(c, "estimate")
    if not c.tier:
        raise AppError("bad_state", "ابتدا گروه پرونده را تعیین کنید.", 409)
    total = sum(int(i["qty"]) * int(i["unit_cost_rial"]) for i in items)
    free_cap, pct, sub, prog = compute_split(db, c.tier, total)
    for old in db.scalars(select(CaseEstimate).where(CaseEstimate.case_id == c.id, CaseEstimate.status == "sent")):
        old.status = "superseded"
    est = CaseEstimate(case_id=c.id, items=items, total_cost_rial=total, free_cap_rial=free_cap, subscriber_share_pct=pct,
                       subscriber_share_rial=sub, program_share_rial=prog, created_by=staff.id, note=note,
                       status="sent" if sub > 0 else "accepted")
    db.add(est)
    db.flush()
    if sub > 0:
        # R19: execution waits for the subscriber's own approval in the app.
        _move(db, c, staff.actor, "estimate", "awaiting_consent", note, request)
        notify(db, user_id=c.user_id, kind="estimate_sent", title="برآورد هزینهٔ بهینه‌سازی آماده است",
               body=f"سهم شما از هزینه {jalali.to_fa_digits(f'{sub // 10:,}')} تومان است. برای شروع کار، برآورد را تأیید کنید.",
               data={"route": "/case"}, sms_text="گازیار: برآورد هزینهٔ بهینه‌سازی برای تأیید شما ارسال شد.")
    else:
        _move(db, c, staff.actor, "estimate", "in_execution", note, request)
    return est


def respond_estimate(db: Session, c: Case, user_id: int, accept: bool, request: Request | None) -> Case:
    if c.user_id != user_id:
        raise AppError("not_found", "پرونده پیدا نشد.", 404)
    if c.status != "awaiting_consent":
        raise AppError("bad_state", "برآوردی برای تأیید وجود ندارد.", 409)
    est = db.scalar(select(CaseEstimate).where(CaseEstimate.case_id == c.id, CaseEstimate.status == "sent"))
    if est is None:
        raise AppError("bad_state", "برآوردی برای تأیید وجود ندارد.", 409)
    est.status, est.responded_at = ("accepted" if accept else "declined"), clock.now()
    actor = audit.Actor("user", user_id)
    _move(db, c, actor, "consent" if accept else "decline", "consent_given" if accept else "consent_declined", None, request)
    if c.ambassador_id:
        notify(db, staff_id=c.ambassador_id, kind="consent_" + ("given" if accept else "declined"),
               title="مشترک برآورد را " + ("تأیید کرد" if accept else "رد کرد"), data={"route": f"/cases/{c.id}"})
    return c


def mark_executed(db: Session, c: Case, staff: StaffCtx, note: str | None, request: Request | None) -> Case:
    _require(c, "executed")
    if c.needs_field_visit and not db.scalar(select(CasePhoto.id).where(CasePhoto.case_id == c.id, CasePhoto.phase == "after")):
        raise AppError("photos_required", "ابتدا تصاویر «بعد از اقدام» را ثبت کنید.", 409)
    c.executed = True
    _move(db, c, staff.actor, "executed", "pending_final_approval", note, request)
    return c


def submit_for_final(db: Session, c: Case, staff: StaffCtx, note: str | None, request: Request | None) -> Case:
    """For cases without execution (education only, or visited with nothing to execute)."""
    _require(c, "submit_final")
    if c.status == "evaluated" and c.needs_field_visit:
        raise AppError("bad_state", "این پرونده به بازدید حضوری نیاز دارد.", 409)
    _move(db, c, staff.actor, "submit_final", "pending_final_approval", note, request)
    for tech in db.scalars(select(StaffUser).where(StaffUser.is_active.is_(True))).all():
        if "technician" in (tech.roles or []):
            notify(db, staff_id=tech.id, kind="case_final_pending", title="پرونده آمادهٔ تأیید نهایی است",
                   data={"route": f"/cases/{c.id}"})
    return c


def final_approve(db: Session, c: Case, staff: StaffCtx, note: str | None, request: Request | None) -> Case:
    """Final technical approval → deposit permit for points (flowchart module 3, R20, R23)."""
    from app.modules.points import service as points

    _require(c, "final_approve")
    c.technician_id, c.completed_at = staff.id, clock.now()
    _move(db, c, staff.actor, "final_approve", "completed", note, request)
    reached = db.scalar(select(CaseCall.id).where(CaseCall.case_id == c.id, CaseCall.outcome == "reached"))
    has_checklist = db.scalar(select(CaseChecklist.id).where(CaseChecklist.case_id == c.id))
    awarded = []
    if reached and has_checklist:
        e = points.award(db, user_id=c.user_id, event_type="ambassador_cooperation", idempotency_key=f"case_coop:{c.id}",
                         ref_type="case", ref_id=c.id)
        awarded.append(e)
    if c.executed:
        e = points.award(db, user_id=c.user_id, event_type="optimization_executed", idempotency_key=f"case_exec:{c.id}",
                         ref_type="case", ref_id=c.id)
        awarded.append(e)
    total = sum(e.amount for e in awarded if e)
    notify(db, user_id=c.user_id, kind="case_completed", title="پروندهٔ شما با موفقیت تکمیل شد",
           body=(f"{jalali.to_fa_digits(str(total))} امتیاز به کیف پول شما اضافه شد." if total else "از همکاری شما سپاسگزاریم."),
           data={"route": "/wallet"})
    events.emit("case.completed", db=db, case=c)
    return c


def return_to_ambassador(db: Session, c: Case, staff: StaffCtx, note: str, request: Request | None) -> Case:
    _require(c, "return_to_ambassador")
    back = "in_execution" if c.executed else ("visited" if c.needs_field_visit else "evaluated")
    c.executed = False if back == "in_execution" else c.executed
    _move(db, c, staff.actor, "returned", back, note, request)
    if c.ambassador_id:
        notify(db, staff_id=c.ambassador_id, kind="case_returned", title="پرونده برای اصلاح برگشت داده شد", body=note,
               data={"route": f"/cases/{c.id}"})
    return c


def close(db: Session, c: Case, staff: StaffCtx, status: str, reason: str, request: Request | None) -> Case:
    if c.status in ("completed", "cancelled", "closed_no_action"):
        raise AppError("bad_state", "پرونده قبلاً بسته شده است.", 409)
    if status not in ("cancelled", "closed_no_action"):
        raise AppError("validation_error", "وضعیت بستن معتبر نیست.", 422)
    c.closed_reason, c.completed_at = reason, clock.now()
    for v in db.scalars(select(CaseVisit).where(CaseVisit.case_id == c.id, CaseVisit.status == "scheduled")):
        v.status = "cancelled"
    _move(db, c, staff.actor, status, status, reason, request)
    return c


# ───────────────────────── event handlers ─────────────────────────

@events.on("reading.approved")
def _on_reading_approved(db: Session, reading: Any) -> None:
    """R14 two-level evaluation after the initial reading approval (R43: record + smart assignment)."""
    from app.modules.subscribers import service as subscribers

    user = db.get(User, reading.user_id)
    sub = db.get(Subscriber, reading.subscriber_id)
    if user is None or sub is None:
        return
    # Level A — threshold filter (the threshold or the baseline may have changed since signup).
    if not subscribers.is_eligible(db, sub):
        if user.eligibility != "below_threshold":
            user.eligibility = "below_threshold"
            notify(db, user_id=user.id, kind="below_threshold", title="وضعیت طرح",
                   body="اطلاعات واردشده برای این طرح قابل تأیید نیست؛ لطفاً با پشتیبانی تماس بگیرید.")
        return
    user.eligibility = "eligible"
    # Level B — specialist monitoring: open the case once (a past completed case is not reopened automatically).
    if db.scalar(select(Case.id).where(Case.user_id == user.id)) is None:
        open_case(db, user=user, reason="first_approved_reading", reading_id=reading.id)
