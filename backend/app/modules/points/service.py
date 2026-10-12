"""Points ledger — the only writer of points (ARCHITECTURE §3.6, §5).

Lifecycle: award() creates a `pending` entry that becomes `available` at the
first instant of the next Jalali month (R20: usable at the end of each month).
Spending writes negative `available` entries; refunds write positive ones.
"""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core import audit, clock, jalali
from app.core.errors import AppError
from app.modules.points.models import PointsLedger, PointsRule

DEFAULT_RULES: tuple[tuple[str, str, int, bool], ...] = (
    # (event_type, title_fa, points, per_unit) — initial values from R23; editable in the panel.
    ("signup", "ثبت‌نام تأییدشده", 100, False),
    ("profile_completed", "تکمیل پروفایل و تأیید قوانین", 20, False),
    ("valid_reading", "ثبت قرائت معتبر ماهانه", 30, False),
    ("consumption_reduction", "کاهش مصرف تأییدشده (به ازای هر درصد)", 10, True),
    ("ambassador_cooperation", "همکاری با سفیر و تکمیل فرم بازدید", 50, False),
    ("referral_success", "معرفی موفق", 100, False),
    ("survey_completed", "پاسخ به نظرسنجی", 10, False),
    ("optimization_executed", "اجرای بهینه‌سازی", 50, False),
)
SYSTEM_EVENTS = {"manual_adjustment": "اصلاح دستی", "redemption": "استفاده از امتیاز", "redemption_refund": "بازگشت امتیاز"}


@dataclass
class Balance:
    available: int
    pending: int
    suspended: int

    @property
    def total(self) -> int:
        return self.available + self.pending


def seed_rules(db: Session) -> None:
    existing = set(db.scalars(select(PointsRule.event_type)).all())
    for et, title, pts, per_unit in DEFAULT_RULES:
        if et not in existing:
            db.add(PointsRule(event_type=et, title_fa=title, points=pts, per_unit=per_unit))
    db.flush()


def rule(db: Session, event_type: str) -> PointsRule | None:
    r = db.scalar(select(PointsRule).where(PointsRule.event_type == event_type))
    if r is None and event_type in {e for e, *_ in DEFAULT_RULES}:
        seed_rules(db)
        r = db.scalar(select(PointsRule).where(PointsRule.event_type == event_type))
    return r


def award(db: Session, *, user_id: int, event_type: str, idempotency_key: str, reason: str | None = None,
          units: float = 1, ref_type: str | None = None, ref_id: str | int | None = None,
          period_key: str | None = None, cap_override: int | None = None,
          created_by_staff_id: int | None = None) -> PointsLedger | None:
    """Award points for an event. Returns None when inactive/zero/already awarded/over cap.

    Idempotent: the same idempotency_key can never pay twice, even under races
    (unique index + savepoint).
    """
    r = rule(db, event_type)
    if r is None or not r.is_active or r.points <= 0:
        return None
    if db.scalar(select(PointsLedger.id).where(PointsLedger.idempotency_key == idempotency_key)) is not None:
        return None
    amount = int(round(r.points * units)) if r.per_unit else r.points
    cap = cap_override if cap_override is not None else r.monthly_cap_points
    now = clock.now()
    pk = period_key or jalali.period_key(now)
    if cap is not None:
        used = db.scalar(select(func.coalesce(func.sum(PointsLedger.amount), 0)).where(
            PointsLedger.user_id == user_id, PointsLedger.event_type == event_type,
            PointsLedger.period_key == pk, PointsLedger.status != "reversed")) or 0
        amount = min(amount, max(0, cap - int(used)))
    if amount <= 0:
        return None
    entry = PointsLedger(
        user_id=user_id, event_type=event_type, amount=amount, status="pending", reason=reason or r.title_fa,
        ref_type=ref_type, ref_id=None if ref_id is None else str(ref_id), idempotency_key=idempotency_key,
        period_key=pk, available_at=jalali.next_month_start_utc(now), created_by_staff_id=created_by_staff_id,
    )
    try:
        with db.begin_nested():
            db.add(entry)
            db.flush()
    except IntegrityError:
        return None  # lost a race with an identical award — that is the point of the key
    audit.record(db, audit.SYSTEM if created_by_staff_id is None else audit.Actor("staff", created_by_staff_id),
                 "points.award", "points_ledger", entry.id, None,
                 {"user_id": user_id, "event_type": event_type, "amount": amount, "key": idempotency_key})
    return entry


def balance(db: Session, user_id: int) -> Balance:
    rows = db.execute(select(PointsLedger.status, func.coalesce(func.sum(PointsLedger.amount), 0))
                      .where(PointsLedger.user_id == user_id).group_by(PointsLedger.status)).all()
    by = {s: int(v) for s, v in rows}
    return Balance(by.get("available", 0), by.get("pending", 0), by.get("suspended", 0))


def release_due(db: Session) -> int:
    """pending → available for entries whose month has ended. Idempotent; run daily."""
    now = clock.now()
    rows = db.scalars(select(PointsLedger).where(PointsLedger.status == "pending",
                                                 PointsLedger.available_at <= now)).all()
    for e in rows:
        e.status = "available"
    db.flush()
    return len(rows)


def spend(db: Session, *, user_id: int, amount: int, idempotency_key: str, reason: str, ref_type: str,
          ref_id: str | int) -> PointsLedger:
    if amount <= 0:
        raise ValueError("amount must be positive")
    # Lock the user's ledger rows to serialise concurrent redemptions (PostgreSQL); SQLite serialises writes anyway.
    db.execute(select(PointsLedger.id).where(PointsLedger.user_id == user_id).with_for_update())
    if balance(db, user_id).available < amount:
        raise AppError("insufficient_points", "امتیاز قابل‌استفادهٔ شما کافی نیست.", 409)
    entry = PointsLedger(user_id=user_id, event_type="redemption", amount=-amount, status="available",
                         reason=reason, ref_type=ref_type, ref_id=str(ref_id), idempotency_key=idempotency_key,
                         period_key=jalali.period_key(clock.now()))
    db.add(entry)
    db.flush()
    return entry


def refund(db: Session, *, user_id: int, amount: int, idempotency_key: str, reason: str, ref_type: str,
           ref_id: str | int) -> PointsLedger | None:
    if db.scalar(select(PointsLedger.id).where(PointsLedger.idempotency_key == idempotency_key)) is not None:
        return None
    entry = PointsLedger(user_id=user_id, event_type="redemption_refund", amount=amount, status="available",
                         reason=reason, ref_type=ref_type, ref_id=str(ref_id), idempotency_key=idempotency_key,
                         period_key=jalali.period_key(clock.now()))
    db.add(entry)
    db.flush()
    return entry


def adjust(db: Session, *, user_id: int, amount: int, reason: str, staff: audit.Actor) -> PointsLedger:
    """Manual correction by finance/admin; always audited; applies immediately."""
    if amount == 0:
        raise AppError("bad_amount", "مقدار اصلاح نمی‌تواند صفر باشد.", 422)
    if amount < 0 and balance(db, user_id).available < -amount:
        raise AppError("insufficient_points", "امتیاز قابل‌استفادهٔ کاربر برای کسر کافی نیست.", 409)
    now = clock.now()
    entry = PointsLedger(user_id=user_id, event_type="manual_adjustment", amount=amount, status="available",
                         reason=reason, idempotency_key=f"adjust:{user_id}:{now.timestamp()}:{staff.id}",
                         period_key=jalali.period_key(now), created_by_staff_id=staff.id)
    db.add(entry)
    db.flush()
    audit.record(db, staff, "points.adjust", "points_ledger", entry.id, None, {"user_id": user_id, "amount": amount, "reason": reason})
    return entry


def suspend(db: Session, entry_id: int, reason: str, staff: audit.Actor) -> PointsLedger:
    """Freeze suspicious points (R24, R40). Only positive pending/available entries."""
    e = db.get(PointsLedger, entry_id)
    if e is None:
        raise AppError("not_found", "ردیف امتیاز پیدا نشد.", 404)
    if e.amount <= 0 or e.status not in ("pending", "available"):
        raise AppError("bad_state", "این ردیف قابل تعلیق نیست.", 409)
    if e.status == "available" and balance(db, e.user_id).available < e.amount:
        raise AppError("already_spent", "این امتیاز قبلاً استفاده شده است.", 409)
    before = {"status": e.status}
    e.status_before_suspend, e.status = e.status, "suspended"
    e.suspended_reason, e.suspended_by, e.suspended_at = reason, staff.id, clock.now()
    audit.record(db, staff, "points.suspend", "points_ledger", e.id, before, {"status": "suspended", "reason": reason})
    return e


def unsuspend(db: Session, entry_id: int, staff: audit.Actor, *, reverse: bool = False) -> PointsLedger:
    e = db.get(PointsLedger, entry_id)
    if e is None or e.status != "suspended":
        raise AppError("bad_state", "این ردیف معلق نیست.", 409)
    if reverse:
        e.status = "reversed"
    else:
        restored = e.status_before_suspend or "pending"
        # If its month already ended while suspended, it is available now.
        if restored == "pending" and e.available_at and e.available_at <= clock.now():
            restored = "available"
        e.status = restored
    audit.record(db, staff, "points.reverse" if reverse else "points.unsuspend", "points_ledger", e.id,
                 {"status": "suspended"}, {"status": e.status})
    return e


def suspend_by_ref(db: Session, *, ref_type: str, ref_id: str | int, reason: str, staff: audit.Actor) -> int:
    rows = db.scalars(select(PointsLedger).where(PointsLedger.ref_type == ref_type, PointsLedger.ref_id == str(ref_id),
                                                 PointsLedger.status.in_(("pending", "available")),
                                                 PointsLedger.amount > 0)).all()
    n = 0
    for e in rows:
        try:
            suspend(db, e.id, reason, staff)
            n += 1
        except AppError:
            continue
    return n


def event_title(db: Session, event_type: str) -> str:
    if event_type in SYSTEM_EVENTS:
        return SYSTEM_EVENTS[event_type]
    r = db.scalar(select(PointsRule.title_fa).where(PointsRule.event_type == event_type))
    return r or event_type
