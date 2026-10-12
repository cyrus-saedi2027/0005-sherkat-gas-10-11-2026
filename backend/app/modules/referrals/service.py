"""Referrals. Stage 1 records them at signup; qualification/rewarding is in stage 2."""

from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core import settings_registry as reg
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
