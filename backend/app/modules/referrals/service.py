"""Referrals (R24, R40): recorded at signup, paid only after the referee's first approved reading."""

from __future__ import annotations

from fastapi import Request
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core import audit, clock, events, jalali
from app.core import settings_registry as reg
from app.core.errors import AppError
from app.modules.referrals.models import Referral
from app.modules.users.models import User, UserDevice


def register(db: Session, *, referee: User, code: str | None, device_id: str | None) -> Referral | None:
    if not code:
        return None
    code = code.strip().upper()
    referrer = db.scalar(select(User).where(User.referral_code == code))
    if referrer is None or referrer.id == referee.id:
        return None  # unknown/self codes are silently ignored — never block a signup over it
    signals: dict[str, object] = {}
    if device_id:
        if db.scalar(select(UserDevice.id).where(UserDevice.user_id == referrer.id, UserDevice.device_id == device_id)):
            signals["same_device_as_referrer"] = True
        n = db.scalar(select(func.count(func.distinct(UserDevice.user_id))).where(UserDevice.device_id == device_id)) or 0
        if n > reg.get_int(db, "fraud.max_accounts_per_device"):
            signals["device_shared_by"] = int(n)
    referee.referred_by_user_id = referrer.id
    r = Referral(referrer_user_id=referrer.id, referee_user_id=referee.id, code_used=code, signals=signals)
    db.add(r)
    db.flush()
    return r


# ───────────────────────── stage 2: qualification & review (R24, R40) ─────────────────────────




def _rewarded_this_month(db: Session, referrer_id: int, period: str) -> int:
    return int(db.scalar(select(func.count()).where(Referral.referrer_user_id == referrer_id, Referral.status == "rewarded",
                                                    Referral.period_key == period)) or 0)


def _pay(db: Session, r: Referral, actor: audit.Actor) -> bool:
    from app.modules.points import service as points

    e = points.award(db, user_id=r.referrer_user_id, event_type="referral_success", idempotency_key=f"referral:{r.referee_user_id}",
                     ref_type="referral", ref_id=r.id, reason="معرفی موفق یک مشترک جدید",
                     created_by_staff_id=actor.id if actor.type == "staff" else None)
    return e is not None


def qualify(db: Session, referee_user_id: int) -> Referral | None:
    """Called on the referee's first approved reading — the "first real activity" of R24."""
    from app.modules.notifications.service import notify

    r = db.scalar(select(Referral).where(Referral.referee_user_id == referee_user_id))
    if r is None or r.status != "pending":
        return None
    now = clock.now()
    r.qualified_at, r.period_key = now, jalali.period_key(now)
    referrer = db.get(User, r.referrer_user_id)
    if referrer is None or referrer.status != "active":
        r.status, r.reason = "rejected", "حساب معرف فعال نیست."
        return r
    if r.signals:
        r.status = "suspicious"  # finance decides (R40)
        r.reason = "نشانه‌های مشکوک: " + "، ".join(sorted(r.signals))
        return r
    if _rewarded_this_month(db, r.referrer_user_id, r.period_key) >= reg.get_int(db, "fraud.referral_monthly_cap"):
        r.status, r.reason = "capped", "سقف معرفی ماهانه پر شده است."
        return r
    if _pay(db, r, audit.SYSTEM):
        r.status = "rewarded"
        notify(db, user_id=r.referrer_user_id, kind="referral_rewarded", title="امتیاز معرفی به حساب شما اضافه شد",
               body="فردی که معرفی کرده بودید اولین قرائت معتبر خود را ثبت کرد.", data={"route": "/wallet"})
    return r


def review(db: Session, referral_id: int, approve: bool, reason: str, staff: audit.Actor, request: Request | None) -> Referral:
    r = db.get(Referral, referral_id)
    if r is None:
        raise AppError("not_found", "معرفی پیدا نشد.", 404)
    if r.status not in ("suspicious", "capped"):
        raise AppError("bad_state", "این معرفی نیاز به بررسی ندارد.", 409)
    before = r.status
    if approve:
        if r.status == "capped" and _rewarded_this_month(db, r.referrer_user_id, r.period_key or "") >= \
                reg.get_int(db, "fraud.referral_monthly_cap"):
            raise AppError("cap_reached", "سقف معرفی ماهانهٔ این معرف پر است.", 409)
        r.status = "rewarded" if _pay(db, r, staff) else r.status
    else:
        r.status = "rejected"
    r.reason, r.reviewed_by = reason, staff.id
    audit.record(db, staff, "referral.review", "referral", r.id, {"status": before}, {"status": r.status, "reason": reason}, request)
    return r


@events.on("reading.approved")
def _on_reading_approved(db: Session, reading) -> None:
    from app.modules.readings.models import MeterReading

    first = db.scalar(select(func.count()).where(MeterReading.user_id == reading.user_id, MeterReading.status == "approved"))
    if int(first or 0) == 1:
        qualify(db, reading.user_id)
