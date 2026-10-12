from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core import clock
from app.modules.files import service as files
from app.modules.staff.models import StaffUser
from app.modules.subscribers.models import Subscriber
from app.modules.tickets.models import Ticket, TicketAttachment, TicketEvent, TicketMessage
from app.modules.tickets.schemas import (
    AdminTicketDetail,
    AdminTicketOut,
    AttachmentOut,
    EventOut,
    MessageOut,
    TicketDetail,
    TicketOut,
)
from app.modules.tickets.service import SUBJECTS
from app.modules.users.models import User


def ticket_out(t: Ticket) -> TicketOut:
    return TicketOut(id=t.id, tracking_code=t.tracking_code, subject_key=t.subject_key, subject_fa=SUBJECTS.get(t.subject_key, ""),
                     title=t.title, status=t.status, priority=t.priority, assigned_unit=t.assigned_unit, rating=t.rating,
                     created_at=t.created_at, updated_at=t.updated_at, closed_at=t.closed_at)


def messages(db: Session, t: Ticket, *, include_internal: bool) -> list[MessageOut]:
    stmt = select(TicketMessage).where(TicketMessage.ticket_id == t.id).order_by(TicketMessage.id)
    if not include_internal:
        stmt = stmt.where(TicketMessage.is_internal.is_(False))
    msgs = db.scalars(stmt).all()
    atts: dict[int, list[TicketAttachment]] = {}
    for a in db.scalars(select(TicketAttachment).where(TicketAttachment.message_id.in_([m.id for m in msgs] or [0]))).all():
        atts.setdefault(a.message_id, []).append(a)
    staff_ids = {m.author_id for m in msgs if m.author_type == "staff" and m.author_id}
    names = dict(db.execute(select(StaffUser.id, StaffUser.full_name).where(StaffUser.id.in_(staff_ids))).all()) if staff_ids else {}
    out = []
    for m in msgs:
        if m.author_type == "staff":
            name = names.get(m.author_id) if include_internal else "پشتیبانی گازیار"
        else:
            name = "مشترک" if include_internal else "شما"
        out.append(MessageOut(id=m.id, author_type=m.author_type, author_name=name, body=m.body, is_internal=m.is_internal,
                              attachments=[AttachmentOut(id=a.id, kind=a.kind, url=files.url(a.file_id),
                                                         thumb_url=files.url(a.file_id, "thumb")) for a in atts.get(m.id, [])],
                              created_at=m.created_at))
    return out


def user_detail(db: Session, t: Ticket) -> TicketDetail:
    return TicketDetail(**ticket_out(t).model_dump(), messages=messages(db, t, include_internal=False),
                        rating_comment=t.rating_comment, can_reply=t.status != "closed",
                        can_rate=t.status in ("resolved", "closed") and t.rating is None)


def admin_out(db: Session, t: Ticket) -> AdminTicketOut:
    u = db.get(User, t.user_id)
    sub = db.get(Subscriber, u.subscriber_id) if u else None
    assignee = db.get(StaffUser, t.assignee_staff_id) if t.assignee_staff_id else None
    name = " ".join(x for x in ((u.first_name, u.last_name) if u else ()) if x) or (sub.full_name if sub else None)
    return AdminTicketOut(**ticket_out(t).model_dump(), user_id=t.user_id, user_name=name,
                          subscription_no=sub.subscription_no if sub else None, assignee_staff_id=t.assignee_staff_id,
                          assignee_name=assignee.full_name if assignee else None, follow_up_at=t.follow_up_at,
                          last_customer_activity_at=t.last_customer_activity_at, last_staff_activity_at=t.last_staff_activity_at,
                          overdue_follow_up=bool(t.follow_up_at and t.follow_up_at < clock.now() and t.status not in ("resolved", "closed")))


def admin_detail(db: Session, t: Ticket) -> AdminTicketDetail:
    evs = db.scalars(select(TicketEvent).where(TicketEvent.ticket_id == t.id).order_by(TicketEvent.id)).all()
    ids = {e.actor_id for e in evs if e.actor_type == "staff" and e.actor_id}
    names = dict(db.execute(select(StaffUser.id, StaffUser.full_name).where(StaffUser.id.in_(ids))).all()) if ids else {}
    return AdminTicketDetail(**admin_out(db, t).model_dump(), messages=messages(db, t, include_internal=True),
                             events=[EventOut(field=e.field, old=e.old, new=e.new, created_at=e.created_at,
                                              actor_name=names.get(e.actor_id or 0) if e.actor_type == "staff" else "مشترک")
                                     for e in evs], rating_comment=t.rating_comment)
