"""Tickets (R32, R33, R39)."""

from __future__ import annotations

import secrets
from datetime import datetime

from fastapi import Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core import audit, clock, jalali
from app.core.deps import StaffCtx
from app.core.errors import AppError
from app.core.rbac import ticket_units_for
from app.modules.files import service as files
from app.modules.notifications.service import notify
from app.modules.staff.models import StaffUser
from app.modules.tickets.models import Ticket, TicketAttachment, TicketEvent, TicketMessage

SUBJECTS = {"reading": "قرائت کنتور", "points": "امتیاز و کیف پول", "store": "فروشگاه و جوایز", "case": "پرونده و بازدید",
            "technical": "مشکل فنی اپلیکیشن", "account": "حساب کاربری", "other": "سایر"}
UNIT_FOR_SUBJECT = {"reading": "support", "points": "finance", "store": "finance", "case": "technical",
                    "technical": "support", "account": "support", "other": "support"}
CUSTOMER_CLOSED = ("resolved", "closed")


def staff_units(staff: StaffCtx) -> set[str]:
    return set(ticket_units_for(staff.roles))


def can_see(staff: StaffCtx, t: Ticket) -> bool:
    if "super_admin" in staff.roles:
        return True
    if t.assignee_staff_id == staff.id:
        return True
    return t.assigned_unit in staff_units(staff)


def _code(db: Session) -> str:
    j = jalali.jdate_of(clock.now())
    for _ in range(20):
        code = f"GZ-{j.year % 100:02d}{j.month:02d}{j.day:02d}-{secrets.randbelow(100000):05d}"
        if db.scalar(select(Ticket.id).where(Ticket.tracking_code == code)) is None:
            return code
    raise RuntimeError("tracking code space exhausted")


def _attach(db: Session, msg: TicketMessage, uploads: list[tuple[bytes, str | None, str]], owner_type: str, owner_id: int) -> None:
    for raw, name, kind in uploads[:5]:
        f = files.save_image(db, raw, purpose="ticket_attachment", owner_type=owner_type, owner_id=owner_id, original_name=name)
        db.add(TicketAttachment(message_id=msg.id, file_id=f.id, kind=kind if kind in ("meter_photo", "receipt", "invoice") else "other"))


def _log(db: Session, t: Ticket, actor: audit.Actor, field: str, old: str | None, new: str | None) -> None:
    db.add(TicketEvent(ticket_id=t.id, actor_type=actor.type, actor_id=actor.id, field=field, old=old, new=new))


def create(db: Session, *, user_id: int, subject_key: str, title: str, body: str,
           uploads: list[tuple[bytes, str | None, str]], request: Request | None) -> Ticket:
    if subject_key not in SUBJECTS:
        raise AppError("validation_error", "موضوع انتخاب‌شده معتبر نیست.", 422)
    now = clock.now()
    t = Ticket(tracking_code=_code(db), user_id=user_id, subject_key=subject_key, title=title.strip(),
               assigned_unit=UNIT_FOR_SUBJECT[subject_key], last_customer_activity_at=now)
    db.add(t)
    db.flush()
    m = TicketMessage(ticket_id=t.id, author_type="user", author_id=user_id, body=body.strip())
    db.add(m)
    db.flush()
    _attach(db, m, uploads, "user", user_id)
    _notify_unit(db, t, "تیکت جدید", f"{t.tracking_code} — {t.title}")
    audit.record(db, audit.Actor("user", user_id), "ticket.create", "ticket", t.id, None,
                 {"code": t.tracking_code, "subject": subject_key}, request)
    return t


def _notify_unit(db: Session, t: Ticket, title: str, body: str) -> None:
    """R33: support receives the ticket notice — the assignee, or everyone working that unit."""
    if t.assignee_staff_id:
        notify(db, staff_id=t.assignee_staff_id, kind="ticket", title=title, body=body, data={"route": f"/tickets/{t.id}"})
        return
    for st in db.scalars(select(StaffUser).where(StaffUser.is_active.is_(True))).all():
        if t.assigned_unit in ticket_units_for(st.roles or []) and "super_admin" not in (st.roles or []):
            notify(db, staff_id=st.id, kind="ticket", title=title, body=body, data={"route": f"/tickets/{t.id}"})


def user_reply(db: Session, t: Ticket, user_id: int, body: str, uploads, request: Request | None) -> TicketMessage:
    if t.user_id != user_id:
        raise AppError("not_found", "تیکت پیدا نشد.", 404)
    if t.status == "closed":
        raise AppError("bad_state", "این تیکت بسته شده است؛ تیکت جدید ثبت کنید.", 409)
    m = TicketMessage(ticket_id=t.id, author_type="user", author_id=user_id, body=body.strip())
    db.add(m)
    db.flush()
    _attach(db, m, uploads, "user", user_id)
    t.last_customer_activity_at = clock.now()
    if t.status in ("awaiting_customer", "answered", "resolved"):
        _log(db, t, audit.Actor("user", user_id), "status", t.status, "open")
        t.status = "open"
    _notify_unit(db, t, "پاسخ جدید مشتری", t.tracking_code)
    return m


def staff_reply(db: Session, t: Ticket, staff: StaffCtx, body: str, internal: bool, uploads,
                set_status: str | None, request: Request | None) -> TicketMessage:
    if not can_see(staff, t):
        raise AppError("not_found", "تیکت پیدا نشد.", 404)
    m = TicketMessage(ticket_id=t.id, author_type="staff", author_id=staff.id, body=body.strip(), is_internal=internal)
    db.add(m)
    db.flush()
    _attach(db, m, uploads, "staff", staff.id)
    if not internal:
        t.last_staff_activity_at = clock.now()
        new_status = set_status or "answered"
        if new_status != t.status:
            _log(db, t, staff.actor, "status", t.status, new_status)
            t.status = new_status
        notify(db, user_id=t.user_id, kind="ticket_reply", title="پاسخ پشتیبانی به تیکت شما",
               body=f"تیکت {t.tracking_code}", data={"route": f"/tickets/{t.id}"})
    audit.record(db, staff.actor, "ticket.note" if internal else "ticket.reply", "ticket", t.id, request=request)
    return m


def update(db: Session, t: Ticket, staff: StaffCtx, *, status: str | None, priority: str | None, unit: str | None,
           assignee_id: int | None, clear_assignee: bool, follow_up_at: datetime | None, clear_follow_up: bool,
           request: Request | None) -> Ticket:
    if not can_see(staff, t):
        raise AppError("not_found", "تیکت پیدا نشد.", 404)
    changes = {}
    if status and status != t.status:
        _log(db, t, staff.actor, "status", t.status, status)
        changes["status"] = (t.status, status)
        t.status = status
        if status in CUSTOMER_CLOSED:
            t.closed_at = clock.now()
            notify(db, user_id=t.user_id, kind="ticket_closed", title="تیکت شما بسته شد",
                   body="لطفاً به کیفیت پاسخگویی امتیاز دهید.", data={"route": f"/tickets/{t.id}"})
        if status == "awaiting_customer":
            notify(db, user_id=t.user_id, kind="ticket_waiting", title="پشتیبانی منتظر پاسخ شماست",
                   body=f"تیکت {t.tracking_code}", data={"route": f"/tickets/{t.id}"})
    if priority and priority != t.priority:
        _log(db, t, staff.actor, "priority", t.priority, priority)
        t.priority = priority
    if unit and unit != t.assigned_unit:
        # R33/R39: refer to an expert or another unit (internal referral)
        _log(db, t, staff.actor, "unit", t.assigned_unit, unit)
        t.assigned_unit, t.assignee_staff_id = unit, None
        _notify_unit(db, t, "تیکت به واحد شما ارجاع شد", f"{t.tracking_code} — {t.title}")
    if clear_assignee and t.assignee_staff_id:
        _log(db, t, staff.actor, "assignee", str(t.assignee_staff_id), None)
        t.assignee_staff_id = None
    elif assignee_id and assignee_id != t.assignee_staff_id:
        st = db.get(StaffUser, assignee_id)
        if st is None or not st.is_active:
            raise AppError("validation_error", "کارشناس انتخاب‌شده معتبر نیست.", 422)
        _log(db, t, staff.actor, "assignee", str(t.assignee_staff_id or ""), str(assignee_id))
        t.assignee_staff_id = assignee_id
        if assignee_id != staff.id:
            notify(db, staff_id=assignee_id, kind="ticket", title="تیکت به شما ارجاع شد", body=t.tracking_code,
                   data={"route": f"/tickets/{t.id}"})
    if clear_follow_up:
        t.follow_up_at = None
    elif follow_up_at:
        _log(db, t, staff.actor, "follow_up", None, follow_up_at.isoformat())
        t.follow_up_at = follow_up_at
    audit.record(db, staff.actor, "ticket.update", "ticket", t.id, None, {k: v[1] for k, v in changes.items()} or None, request)
    return t


def rate(db: Session, t: Ticket, user_id: int, rating: int, comment: str | None) -> Ticket:
    """R32: after completion the customer rates the answer quality (the satisfaction survey of R39)."""
    if t.user_id != user_id:
        raise AppError("not_found", "تیکت پیدا نشد.", 404)
    if t.status not in CUSTOMER_CLOSED:
        raise AppError("bad_state", "امتیازدهی بعد از بسته شدن تیکت امکان‌پذیر است.", 409)
    if t.rating is not None:
        raise AppError("already_rated", "قبلاً به این تیکت امتیاز داده‌اید.", 409)
    t.rating, t.rating_comment, t.rated_at = rating, (comment or "").strip()[:500] or None, clock.now()
    if t.status == "resolved":
        t.status = "closed"
    return t
