"""Model → schema mapping shared by app and admin routers."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core import jalali
from app.modules.files import service as files
from app.modules.readings.models import MeterReading, ReadingEvent
from app.modules.readings.reasons import REJECT_REASONS
from app.modules.readings.schemas import ReadingEventOut, ReadingOut
from app.modules.staff.models import StaffUser


def reading_out(r: MeterReading, *, for_staff: bool = False) -> ReadingOut:
    return ReadingOut(
        id=r.id, period_key=r.period_key, period_label=jalali.period_label(r.period_key), revision=r.revision,
        kind=r.kind, is_current=r.is_current, input_method=r.input_method, declared_value=r.declared_value,
        approved_value=r.approved_value, reading_date=r.reading_date, status=r.status, reason_code=r.reason_code,
        reason_text=REJECT_REASONS.get(r.reason_code or "") if r.reason_code else None, review_note=r.review_note,
        user_note=r.user_note, consumption_m3=r.consumption_m3, baseline_m3=r.baseline_m3,
        reduction_pct=r.reduction_pct, photo_url=files.url(r.photo_file_id),
        photo_thumb_url=files.url(r.photo_file_id, "thumb"), created_at=r.created_at, reviewed_at=r.reviewed_at,
        can_resubmit=r.is_current and r.status in ("needs_correction", "approved", "rejected"),
    )


def events_out(db: Session, reading_ids: list[int], *, for_staff: bool) -> list[ReadingEventOut]:
    rows = db.scalars(select(ReadingEvent).where(ReadingEvent.reading_id.in_(reading_ids)).order_by(ReadingEvent.id)).all()
    staff_ids = {e.actor_id for e in rows if e.actor_type == "staff" and e.actor_id}
    names = dict(db.execute(select(StaffUser.id, StaffUser.full_name).where(StaffUser.id.in_(staff_ids))).all()) if staff_ids else {}
    out = []
    for e in rows:
        o = ReadingEventOut.model_validate(e, from_attributes=True)
        if e.actor_type == "staff":
            # Users see "کارشناس", never the operator's name or id.
            o.actor_name = names.get(e.actor_id) if for_staff else "کارشناس"
            if not for_staff:
                o.actor_id = None
        out.append(o)
    return out


def revisions(db: Session, r: MeterReading) -> list[MeterReading]:
    return list(db.scalars(select(MeterReading).where(MeterReading.subscriber_id == r.subscriber_id,
                                                      MeterReading.period_key == r.period_key)
                           .order_by(MeterReading.revision)).all())
