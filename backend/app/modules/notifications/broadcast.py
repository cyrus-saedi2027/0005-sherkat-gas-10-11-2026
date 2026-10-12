"""Segmented broadcasts to subscribers (R46). In-app rows are bulk-inserted; SMS goes through the outbox."""

from __future__ import annotations

from typing import Any

from fastapi import Request
from sqlalchemy import insert, select
from sqlalchemy.orm import Session

from app.core import audit, clock, crypto, sms
from app.modules.notifications.models import Broadcast, Notification
from app.modules.regions.service import descendants
from app.modules.subscribers.models import Subscriber
from app.modules.users.models import User


def audience(db: Session, segment: dict[str, Any]):
    stmt = select(User.id, User.mobile_enc).join(Subscriber, Subscriber.id == User.subscriber_id).where(User.status == "active")
    if segment.get("region_ids"):
        ids: set[int] = set()
        for r in segment["region_ids"]:
            ids |= descendants(db, int(r))
        stmt = stmt.where(Subscriber.region_id.in_(ids))
    tiers = segment.get("tiers") or []
    if tiers:
        conds = [t for t in tiers if t != "none"]
        if "none" in tiers:
            stmt = stmt.where((User.tier.in_(conds)) | (User.tier.is_(None)))
        else:
            stmt = stmt.where(User.tier.in_(conds))
    if segment.get("eligibility"):
        stmt = stmt.where(User.eligibility == segment["eligibility"])
    return stmt


def count(db: Session, segment: dict[str, Any]) -> int:
    return len(db.execute(audience(db, segment)).all())


def send(db: Session, *, title: str, body: str, channels: list[str], segment: dict[str, Any], route: str | None,
         actor: audit.Actor, request: Request | None) -> Broadcast:
    rows = db.execute(audience(db, segment)).all()
    b = Broadcast(title=title, body=body, channels=channels, segment=segment, route=route, recipients=len(rows), created_by=actor.id or 0)
    db.add(b)
    db.flush()
    now = clock.now()
    if "in_app" in channels and rows:
        payload = [{"recipient_type": "user", "recipient_id": uid, "kind": "broadcast", "title": title, "body": body,
                    "data": {"route": route} if route else {}, "broadcast_id": b.id, "created_at": now, "updated_at": now}
                   for uid, _ in rows]
        for i in range(0, len(payload), 2000):
            db.execute(insert(Notification), payload[i:i + 2000])
    if "sms" in channels:
        text = f"گازیار: {title}\n{body}"[:600]
        for _, enc in rows:
            sms.queue(db, crypto.decrypt(enc) or "", text, "broadcast")
    audit.record(db, actor, "broadcast.send", "broadcast", b.id, None,
                 {"recipients": len(rows), "channels": channels, "segment": segment}, request)
    return b
