from __future__ import annotations

from fastapi import Request
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core import audit, clock, crypto, security
from app.core.errors import AppError
from app.core.normalize import mask_mobile, normalize_text, to_ascii_digits
from app.core.validators import is_valid_iban, is_valid_national_code, normalize_iban, password_problem
from app.modules.regions.models import Region
from app.modules.subscribers.models import Subscriber
from app.modules.users.models import User, UserDevice
from app.modules.users.schemas import AdminUserDetail, AdminUserOut, MeOut, ProfileUpdate


def _mask(v: str | None, keep: int = 4) -> str | None:
    if not v:
        return None
    return "*" * max(0, len(v) - keep) + v[-keep:]


def me_out(db: Session, u: User) -> MeOut:
    sub = db.get(Subscriber, u.subscriber_id)
    region = db.get(Region, sub.region_id) if sub and sub.region_id else None
    return MeOut(id=u.id, first_name=u.first_name, last_name=u.last_name, mobile_masked=mask_mobile(crypto.decrypt(u.mobile_enc)),
                 national_code_masked=_mask(crypto.decrypt(u.national_code_enc), 3),
                 iban_masked=_mask(crypto.decrypt(u.iban_enc), 4), subscription_no=sub.subscription_no if sub else "",
                 region_name=region.name if region else None, login_method=u.login_method,
                 has_password=bool(u.password_hash), referral_code=u.referral_code, tier=u.tier,
                 eligibility=u.eligibility, profile_completed=u.profile_completed_at is not None,
                 terms_version=u.terms_version, created_at=u.created_at)


def update_profile(db: Session, u: User, body: ProfileUpdate, request: Request | None) -> User:
    from app.modules.points import service as points

    data = body.model_dump(exclude_unset=True)
    fields: dict[str, str] = {}
    if "first_name" in data and data["first_name"] is not None:
        u.first_name = normalize_text(data["first_name"])[:80]
    if "last_name" in data and data["last_name"] is not None:
        u.last_name = normalize_text(data["last_name"])[:80]
    if data.get("national_code"):
        nc = to_ascii_digits(data["national_code"]).replace("-", "").replace(" ", "")
        if not is_valid_national_code(nc):
            fields["national_code"] = "کد ملی معتبر نیست."
        else:
            bidx = crypto.blind_index(nc, purpose="national_code")
            if db.scalar(select(User.id).where(User.national_code_bidx == bidx, User.id != u.id)):
                # One account per person as well as per subscription (R24) — vague on purpose.
                fields["national_code"] = "این کد ملی برای حساب دیگری ثبت شده است؛ با پشتیبانی تماس بگیرید."
            else:
                u.national_code_enc, u.national_code_bidx = crypto.encrypt(nc), bidx
    if data.get("iban"):
        if not is_valid_iban(data["iban"]):
            fields["iban"] = "شماره شبا معتبر نیست."
        else:
            u.iban_enc = crypto.encrypt(normalize_iban(data["iban"]))
    if fields:
        raise AppError("validation_error", "برخی اطلاعات معتبر نیست.", 422, {"fields": fields})
    complete = bool(u.first_name and u.last_name and u.national_code_enc and u.terms_accepted_at)
    if complete and u.profile_completed_at is None:
        u.profile_completed_at = clock.now()
        points.award(db, user_id=u.id, event_type="profile_completed",
                     idempotency_key=f"profile_completed:subscriber:{u.subscriber_id}", ref_type="user", ref_id=u.id)
    audit.record(db, audit.Actor("user", u.id), "user.profile_update", "user", u.id, None,
                 {"fields": sorted(k for k in data if data[k] is not None)}, request)
    return u


def set_password(db: Session, u: User, password: str, login_method: str, request: Request | None) -> None:
    if login_method == "password":
        problem = password_problem(password)
        if problem:
            raise AppError("validation_error", problem, 422, {"fields": {"password": problem}})
        u.password_hash = security.hash_password(password)
    u.login_method = login_method
    audit.record(db, audit.Actor("user", u.id), "user.login_method", "user", u.id, None, {"login_method": login_method}, request)


def admin_out(db: Session, u: User, sub: Subscriber | None, region: Region | None) -> AdminUserOut:
    name = " ".join(x for x in (u.first_name, u.last_name) if x) or (sub.full_name if sub else None)
    return AdminUserOut(id=u.id, full_name=name, mobile_masked=mask_mobile(crypto.decrypt(u.mobile_enc)),
                        subscription_no=sub.subscription_no if sub else "", subscriber_id=u.subscriber_id,
                        region_id=sub.region_id if sub else None, region_name=region.name if region else None,
                        status=u.status, tier=u.tier, eligibility=u.eligibility,
                        profile_completed=u.profile_completed_at is not None, created_at=u.created_at,
                        last_seen_at=u.last_seen_at)


def admin_detail(db: Session, u: User) -> AdminUserDetail:
    from app.modules.points import service as points

    sub = db.get(Subscriber, u.subscriber_id)
    region = db.get(Region, sub.region_id) if sub and sub.region_id else None
    b = points.balance(db, u.id)
    devices = db.scalar(select(func.count()).where(UserDevice.user_id == u.id)) or 0
    return AdminUserDetail(**admin_out(db, u, sub, region).model_dump(),
                           national_code_masked=_mask(crypto.decrypt(u.national_code_enc), 3),
                           iban_masked=_mask(crypto.decrypt(u.iban_enc), 4), referral_code=u.referral_code,
                           referred_by_user_id=u.referred_by_user_id, devices=int(devices),
                           points_available=b.available, points_pending=b.pending, points_suspended=b.suspended)


def set_status(db: Session, u: User, suspend: bool, reason: str, actor: audit.Actor, request: Request | None) -> User:
    before = u.status
    u.status = "suspended" if suspend else "active"
    if suspend:
        from app.modules.auth.service import revoke_all

        revoke_all(db, "user", u.id)
    audit.record(db, actor, "user.suspend" if suspend else "user.unsuspend", "user", u.id, {"status": before},
                 {"status": u.status, "reason": reason}, request)
    return u
