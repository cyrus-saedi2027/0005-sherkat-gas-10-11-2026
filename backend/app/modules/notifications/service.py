"""The ONLY way modules notify people (ARCHITECTURE §5)."""

from __future__ import annotations

from typing import Any

from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from app.core import clock, crypto, sms
from app.modules.notifications.models import Notification


def notify(db: Session, *, user_id: int | None = None, staff_id: int | None = None, kind: str, title: str,
           body: str = "", data: dict[str, Any] | None = None, sms_text: str | None = None,
           broadcast_id: int | None = None) -> Notification:
    if (user_id is None) == (staff_id is None):
        raise ValueError("exactly one recipient")
    n = Notification(recipient_type="user" if user_id is not None else "staff",
                     recipient_id=user_id if user_id is not None else staff_id,  # type: ignore[arg-type]
                     kind=kind, title=title, body=body, data=data or {}, broadcast_id=broadcast_id)
    db.add(n)
    if sms_text and user_id is not None:
        from app.modules.users.models import User

        u = db.get(User, user_id)
        if u is not None:
            sms.queue(db, crypto.decrypt(u.mobile_enc) or "", sms_text, "notify")
    db.flush()
    return n


def list_for(db: Session, recipient_type: str, recipient_id: int, limit: int, offset: int,
             unread_only: bool = False) -> tuple[list[Notification], int, int]:
    base = select(Notification).where(Notification.recipient_type == recipient_type,
                                      Notification.recipient_id == recipient_id)
    if unread_only:
        base = base.where(Notification.read_at.is_(None))
    total = db.scalar(select(func.count()).select_from(base.subquery())) or 0
    unread = db.scalar(select(func.count()).where(Notification.recipient_type == recipient_type,
                                                  Notification.recipient_id == recipient_id,
                                                  Notification.read_at.is_(None))) or 0
    rows = db.scalars(base.order_by(Notification.id.desc()).limit(limit).offset(offset)).all()
    return list(rows), int(total), int(unread)


def mark_read(db: Session, recipient_type: str, recipient_id: int, ids: list[int] | None) -> int:
    stmt = update(Notification).where(Notification.recipient_type == recipient_type,
                                      Notification.recipient_id == recipient_id, Notification.read_at.is_(None))
    if ids is not None:
        stmt = stmt.where(Notification.id.in_(ids[:500]))
    res = db.execute(stmt.values(read_at=clock.now()))
    return int(res.rowcount or 0)  # type: ignore[attr-defined]
