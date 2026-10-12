from __future__ import annotations

from fastapi import APIRouter
from sqlalchemy import select

from app.core import settings_registry as reg
from app.core.deps import DB, CurrentUser
from app.modules.points.service import rule
from app.modules.referrals.models import Referral
from app.modules.referrals.schemas import MyReferralOut, MyReferralsOut
from app.modules.users.models import User

router = APIRouter(prefix="/referrals", tags=["app:referrals"])


@router.get("", response_model=MyReferralsOut)
def mine(user: CurrentUser, db: DB) -> MyReferralsOut:
    me = db.get(User, user.id)
    assert me is not None
    rows = db.scalars(select(Referral).where(Referral.referrer_user_id == user.id).order_by(Referral.id.desc()).limit(100)).all()
    ref_users = {u.id: u for u in db.scalars(select(User).where(User.id.in_([r.referee_user_id for r in rows]))).all()}
    items = []
    for r in rows:
        u = ref_users.get(r.referee_user_id)
        # Privacy: the referrer sees a first name + initial only.
        name = f"{u.first_name or 'کاربر'} {(u.last_name or '')[:1]}.".strip() if u else "کاربر"
        # Internal fraud states are shown as "در حال بررسی" — never reveal the detection.
        status = r.status if r.status in ("pending", "rewarded") else ("under_review" if r.status == "suspicious" else r.status)
        items.append(MyReferralOut(id=r.id, referee_name=name, status=status, created_at=r.created_at, qualified_at=r.qualified_at))
    rr = rule(db, "referral_success")
    return MyReferralsOut(code=me.referral_code,
                          share_text=f"با کد معرف {me.referral_code} در طرح «گازیار» ثبت‌نام کن، با صرفه‌جویی در مصرف گاز جایزه بگیر!",
                          items=items, rewarded=sum(1 for r in rows if r.status == "rewarded"),
                          pending=sum(1 for r in rows if r.status == "pending"),
                          monthly_cap=reg.get_int(db, "fraud.referral_monthly_cap"),
                          points_per_referral=rr.points if rr else 0)
