"""Meter readings: submission, anomaly flags, review decisions (R12, R13, R15, R29, R43, R44)."""

from __future__ import annotations

import math
from datetime import date, timedelta

from fastapi import Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core import audit, clock, events, jalali
from app.core import settings_registry as reg
from app.core.errors import AppError
from app.modules.files import service as files
from app.modules.notifications.service import notify
from app.modules.readings.models import MeterReading, ReadingEvent
from app.modules.readings.reasons import FLAG_FA, REJECT_REASONS
from app.modules.subscribers import service as subscribers
from app.modules.users.models import User

OPEN = ("pending", "flagged")


def _months(db: Session) -> int:
    return int(reg.get(db, "reading.period_months"))


def _event(db: Session, r: MeterReading, actor: audit.Actor, action: str, from_status: str | None,
           to_status: str | None, old: float | None = None, new: float | None = None, reason: str | None = None) -> None:
    db.add(ReadingEvent(reading_id=r.id, actor_type=actor.type, actor_id=actor.id, action=action, from_status=from_status,
                        to_status=to_status, old_value=old, new_value=new, reason=reason))


def current(db: Session, subscriber_id: int, period_key: str) -> MeterReading | None:
    return db.scalar(select(MeterReading).where(MeterReading.subscriber_id == subscriber_id,
                                                MeterReading.period_key == period_key, MeterReading.is_current.is_(True)))


def previous_approved(db: Session, subscriber_id: int, before_period: str) -> MeterReading | None:
    return db.scalar(select(MeterReading).where(
        MeterReading.subscriber_id == subscriber_id, MeterReading.is_current.is_(True),
        MeterReading.status == "approved", MeterReading.period_key < before_period,
    ).order_by(MeterReading.period_key.desc()))


def compute_consumption(db: Session, r: MeterReading, value: float) -> tuple[float | None, float | None, float | None]:
    """(consumption over the period, baseline, reduction %) — normalised to the period length.

    The previous reading may be several periods back (missed months) or a few
    days off the period edges, so we use the daily rate × days in period.
    """
    months = _months(db)
    baseline = subscribers.period_baseline(db, r.subscriber_id, r.period_key, months)
    prev = previous_approved(db, r.subscriber_id, r.period_key)
    if prev is None or prev.approved_value is None or value < prev.approved_value:
        return None, baseline, None
    days = max(1, (r.reading_date - prev.reading_date).days)
    cons = round((value - prev.approved_value) / days * jalali.days_in_period(r.period_key, months), 2)
    red = round((baseline - cons) / baseline * 100, 2) if baseline and baseline > 0 else None
    return cons, baseline, red


def detect_flags(db: Session, r: MeterReading, photo_sha: str | None, exif_taken_at) -> list[str]:
    flags: list[str] = []
    if r.input_method == "manual" and not r.photo_file_id:
        flags.append("manual_no_photo")
    if photo_sha:
        dup = [f for f in files.find_by_sha(db, photo_sha, exclude_id=r.photo_file_id) if f.purpose == "meter_photo"]
        if dup:
            flags.append("duplicate_photo")
    if exif_taken_at is not None:
        delta = abs((jalali.to_tehran(exif_taken_at).date() - r.reading_date).days)
        if delta > reg.get_int(db, "anomaly.exif_max_days"):
            flags.append("exif_mismatch")
    prev = previous_approved(db, r.subscriber_id, r.period_key)
    if prev is not None and prev.approved_value is not None and r.declared_value < prev.approved_value:
        flags.append("meter_rollback")
    cons, baseline, _ = compute_consumption(db, r, r.declared_value)
    if cons is not None:
        if cons <= 0:
            flags.append("zero_consumption")
        elif baseline and baseline > 0:
            if cons < baseline * (1 - reg.get_int(db, "anomaly.sudden_drop_pct") / 100):
                flags.append("sudden_drop")
            elif cons > baseline * reg.get_int(db, "anomaly.spike_pct") / 100:
                flags.append("spike")
    return flags


def submit(db: Session, *, user: User, declared_value: float, reading_date: date, photo: bytes | None,
           photo_name: str | None, user_note: str | None, request: Request | None) -> MeterReading:
    today = jalali.to_tehran(clock.now()).date()
    if reading_date > today:
        raise AppError("validation_error", "تاریخ قرائت نمی‌تواند در آینده باشد.", 422, {"fields": {"reading_date": "تاریخ آینده مجاز نیست."}})
    if reading_date < today - timedelta(days=reg.get_int(db, "reading.max_back_days")):
        raise AppError("validation_error", "تاریخ قرائت خیلی قدیمی است.", 422, {"fields": {"reading_date": "تاریخ خیلی قدیمی است."}})
    if not (0 <= declared_value <= reg.get_int(db, "reading.max_value_m3")) or math.isnan(declared_value):
        raise AppError("validation_error", "عدد کنتور معتبر نیست.", 422, {"fields": {"declared_value": "عدد کنتور معتبر نیست."}})
    if photo is None and bool(reg.get(db, "reading.photo_required")):
        raise AppError("validation_error", "ارسال تصویر کنتور الزامی است.", 422, {"fields": {"photo": "تصویر کنتور را انتخاب کنید."}})
    period = jalali.period_key(reading_date, _months(db))
    cur = current(db, user.subscriber_id, period)
    if cur is not None and cur.status in OPEN:
        raise AppError("reading_pending", "قرائت این دوره در حال بررسی است؛ پس از اعلام نتیجه می‌توانید دوباره ارسال کنید.", 409)
    kind, revision, parent = "initial", 1, None
    if cur is not None:
        kind = "correction" if cur.status == "needs_correction" else "review_request"
        revision, parent = cur.revision + 1, cur.id
        cur.is_current = False
        db.flush()  # free the "current" slot before inserting the new revision
    stored = files.save_image(db, photo, purpose="meter_photo", owner_type="user", owner_id=user.id,
                              original_name=photo_name) if photo is not None else None
    r = MeterReading(user_id=user.id, subscriber_id=user.subscriber_id, period_key=period, revision=revision, kind=kind,
                     parent_id=parent, input_method="photo" if stored else "manual", declared_value=float(declared_value),
                     reading_date=reading_date, photo_file_id=stored.id if stored else None,
                     user_note=(user_note or "").strip()[:500] or None, status="pending")
    db.add(r)
    db.flush()
    r.flags = detect_flags(db, r, stored.sha256 if stored else None, stored.exif_taken_at if stored else None)
    # R15: any pattern inconsistency goes to the manual expert review queue automatically.
    if r.flags:
        r.status = "flagged"
    actor = audit.Actor("user", user.id)
    _event(db, r, actor, "submitted" if kind == "initial" else kind, None, r.status, None, r.declared_value)
    audit.record(db, actor, f"reading.{kind}", "reading", r.id, None,
                 {"period": period, "value": r.declared_value, "flags": r.flags}, request)
    return r


def _require_open(r: MeterReading) -> None:
    if r.status not in OPEN:
        raise AppError("bad_state", "این قرائت قبلاً بررسی شده است.", 409)
    if not r.is_current:
        raise AppError("bad_state", "نسخهٔ جدیدتری از این قرائت ثبت شده است.", 409)


def approve(db: Session, r: MeterReading, *, staff: audit.Actor, can_correct: bool, approved_value: float | None,
            note: str | None, request: Request | None) -> MeterReading:
    _require_open(r)
    value = r.declared_value if approved_value is None else float(approved_value)
    if value != r.declared_value:
        if not can_correct:
            raise AppError("forbidden", "شما اجازهٔ اصلاح عدد کنتور را ندارید.", 403)
        if not (0 <= value <= reg.get_int(db, "reading.max_value_m3")):
            raise AppError("validation_error", "عدد اصلاح‌شده معتبر نیست.", 422)
        _event(db, r, staff, "value_corrected", r.status, r.status, r.declared_value, value, note)
    prev_status = r.status
    r.approved_value = value
    r.consumption_m3, r.baseline_m3, r.reduction_pct = compute_consumption(db, r, value)
    r.status, r.reviewer_id, r.reviewed_at = "approved", staff.id, clock.now()
    r.review_note, r.reason_code, r.claimed_by = (note or None), None, None
    _event(db, r, staff, "approved", prev_status, "approved", r.declared_value, value, note)
    audit.record(db, staff, "reading.approve", "reading", r.id, {"status": prev_status, "value": r.declared_value},
                 {"status": "approved", "value": value}, request)
    _reward(db, r)
    notify(db, user_id=r.user_id, kind="reading_approved", title="قرائت شما تأیید شد",
           body=f"قرائت دورهٔ {jalali.period_label(r.period_key)} تأیید شد.", data={"route": f"/readings/{r.id}"})
    # Stage 2 subscribers: open/advance the technical case, qualify referrals …
    events.emit("reading.approved", db=db, reading=r)
    return r


def _reward(db: Session, r: MeterReading) -> None:
    from app.modules.points import service as points

    # Keyed per subscriber+period: revisions, review requests and re-approvals never pay twice (R13).
    points.award(db, user_id=r.user_id, event_type="valid_reading", idempotency_key=f"valid_reading:{r.subscriber_id}:{r.period_key}",
                 ref_type="reading", ref_id=r.id, period_key=r.period_key)
    required = reg.get_int(db, "points.reduction_required_pct")
    if r.reduction_pct is not None and r.reduction_pct >= max(required, 1e-9):
        points.award(db, user_id=r.user_id, event_type="consumption_reduction",
                     idempotency_key=f"reduction:{r.subscriber_id}:{r.period_key}", units=math.floor(r.reduction_pct),
                     ref_type="reading", ref_id=r.id, period_key=r.period_key,
                     cap_override=reg.get_int(db, "points.reduction_monthly_cap"),
                     reason=f"کاهش {int(r.reduction_pct)}٪ مصرف نسبت به میانگین سه سال قبل")


def needs_correction(db: Session, r: MeterReading, *, staff: audit.Actor, reason_code: str, note: str | None,
                     request: Request | None) -> MeterReading:
    return _close(db, r, staff=staff, to="needs_correction", reason_code=reason_code, note=note, request=request)


def reject(db: Session, r: MeterReading, *, staff: audit.Actor, reason_code: str, note: str | None,
           request: Request | None) -> MeterReading:
    return _close(db, r, staff=staff, to="rejected", reason_code=reason_code, note=note, request=request)


def _close(db: Session, r: MeterReading, *, staff: audit.Actor, to: str, reason_code: str, note: str | None,
           request: Request | None) -> MeterReading:
    _require_open(r)
    if reason_code not in REJECT_REASONS:
        raise AppError("validation_error", "دلیل انتخاب‌شده معتبر نیست.", 422)
    if reason_code == "other" and not (note or "").strip():
        raise AppError("validation_error", "برای «سایر» توضیح لازم است.", 422, {"fields": {"note": "توضیح را بنویسید."}})
    prev = r.status
    r.status, r.reason_code, r.review_note = to, reason_code, (note or "").strip() or None
    r.reviewer_id, r.reviewed_at, r.claimed_by = staff.id, clock.now(), None
    _event(db, r, staff, to, prev, to, reason=f"{REJECT_REASONS[reason_code]} {r.review_note or ''}".strip())
    audit.record(db, staff, f"reading.{to}", "reading", r.id, {"status": prev}, {"status": to, "reason": reason_code}, request)
    reason_fa = REJECT_REASONS[reason_code]
    if to == "needs_correction":
        # R43: tell the user what to fix, in-app AND by SMS.
        notify(db, user_id=r.user_id, kind="reading_needs_correction", title="قرائت شما نیاز به اصلاح دارد",
               body=f"{reason_fa} لطفاً قرائت دورهٔ {jalali.period_label(r.period_key)} را دوباره ارسال کنید.",
               data={"route": f"/readings/{r.id}"}, sms_text=f"گازیار: قرائت شما نیاز به اصلاح دارد. {reason_fa}")
    else:
        notify(db, user_id=r.user_id, kind="reading_rejected", title="قرائت شما تأیید نشد",
               body=f"{reason_fa} در صورت اعتراض می‌توانید درخواست بررسی مجدد ثبت کنید.", data={"route": f"/readings/{r.id}"})
    return r


def claim(db: Session, r: MeterReading, staff_id: int) -> tuple[bool, int | None]:
    """Soft lock for 10 minutes. Returns (claimed_by_me, other_claimer)."""
    now = clock.now()
    if r.claimed_by and r.claimed_by != staff_id and r.claimed_at and r.claimed_at > now - timedelta(minutes=10):
        return False, r.claimed_by
    r.claimed_by, r.claimed_at = staff_id, now
    return True, None


def flag_labels(flags: list[str]) -> list[dict[str, str]]:
    return [{"code": f, "label": FLAG_FA.get(f, f)} for f in flags or []]
