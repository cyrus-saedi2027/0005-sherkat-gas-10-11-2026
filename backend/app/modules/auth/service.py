"""Authentication flows (ARCHITECTURE §4.2).

Subscriber signup: start (eligibility + OTP) → verify (OTP) → complete (terms,
login method, account, signup points). The ineligible path answers with the
exact generic R09 text and does the same work as the eligible path, so neither
the message nor the timing tells an attacker whether a number is on the list.
"""

from __future__ import annotations

import secrets
import uuid
from dataclasses import dataclass
from datetime import timedelta
from typing import Any

import jwt
from fastapi import Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core import audit, clock, crypto, ratelimit, security, sms
from app.core import settings_registry as reg
from app.core.config import get_settings
from app.core.errors import NOT_ELIGIBLE_FA, AppError
from app.core.normalize import mask_mobile, normalize_mobile, normalize_subscription
from app.core.rbac import permissions_for
from app.core.validators import password_problem
from app.modules.auth.models import OtpChallenge, RefreshToken
from app.modules.staff.models import StaffUser
from app.modules.subscribers import service as subscribers
from app.modules.users.models import User, UserDevice

OTP_WRONG_FA = "کد واردشده نادرست است."
OTP_EXPIRED_FA = "کد منقضی شده است؛ دوباره درخواست کد بدهید."
REFERRAL_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"  # no 0/O/1/I — read aloud over the phone


@dataclass
class TokenPair:
    access_token: str
    refresh_token: str
    expires_in: int
    subject_type: str
    subject_id: int


# ───────────────────────── OTP ─────────────────────────

def _code_hash(challenge_id: str, code: str) -> str:
    return crypto.hmac_hex(get_settings().otp_pepper, f"{challenge_id}:{code}")


def _issue_otp(db: Session, *, mobile: str, purpose: str, ip: str, context: dict[str, Any], decoy: bool) -> dict[str, Any]:
    """Create a challenge. Rate limits apply equally to decoys so limits cannot be used as an oracle."""
    bidx = crypto.blind_index(mobile, purpose="mobile") or ""
    ratelimit.enforce(f"otp:ip:{ip}", reg.get_int(db, "otp.per_ip_10min"), 600)
    ratelimit.enforce(f"otp:m10:{bidx}", reg.get_int(db, "otp.per_mobile_10min"), 600,
                      "برای این شماره بیش از حد درخواست کد شده است؛ چند دقیقه بعد تلاش کنید.")
    ratelimit.enforce(f"otp:mday:{bidx}", reg.get_int(db, "otp.per_mobile_day"), 86_400,
                      "سقف دریافت کد برای امروز پر شده است.")
    now = clock.now()
    resend = reg.get_int(db, "otp.resend_seconds")
    recent = db.scalar(select(OtpChallenge).where(
        OtpChallenge.mobile_bidx == bidx, OtpChallenge.purpose == purpose, OtpChallenge.consumed_at.is_(None),
        OtpChallenge.created_at > now - timedelta(seconds=resend)).order_by(OtpChallenge.created_at.desc()))
    if recent is not None:
        wait = int(resend - (now - recent.created_at).total_seconds()) + 1
        raise AppError("otp_cooldown", "کد قبلاً ارسال شده است؛ کمی صبر کنید.", 429, {"retry_after": max(1, wait)})
    ttl = reg.get_int(db, "otp.ttl_seconds")
    cid = uuid.uuid4().hex
    code = security.random_otp(5)
    db.add(OtpChallenge(id=cid, mobile_bidx=bidx, purpose=purpose, code_hash=_code_hash(cid, code),
                        expires_at=now + timedelta(seconds=ttl), ip=ip, context=context, is_decoy=decoy))
    if not decoy:
        sms.queue(db, mobile, f"گازیار\nکد تأیید شما: {code}\nاین کد را در اختیار دیگران قرار ندهید.", "otp", sensitive=True)
    db.flush()
    out: dict[str, Any] = {"challenge_id": cid, "expires_in": ttl, "resend_in": resend, "mobile_masked": mask_mobile(mobile)}
    s = get_settings()
    if s.expose_dev_otp and not s.is_prod and not decoy:
        out["dev_code"] = code
    return out


def _consume_otp(db: Session, challenge_id: str, code: str, purpose: str) -> OtpChallenge:
    ch = db.get(OtpChallenge, challenge_id)
    now = clock.now()
    if ch is None or ch.purpose != purpose or ch.consumed_at is not None or ch.expires_at <= now:
        raise AppError("otp_expired", OTP_EXPIRED_FA, 400)
    if ch.attempts >= reg.get_int(db, "otp.max_attempts"):
        raise AppError("otp_locked", "تعداد تلاش‌ها بیش از حد مجاز است؛ کد جدید بگیرید.", 429)
    ch.attempts += 1
    code = code.strip().translate(str.maketrans("۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩", "01234567890123456789"))
    if ch.is_decoy or not crypto.safe_equals(ch.code_hash, _code_hash(ch.id, code)):
        db.flush()
        # Commit the attempt counter even though we raise (see get_db: errors roll back).
        db.commit()
        raise AppError("otp_wrong", OTP_WRONG_FA, 400, {"attempts_left": max(0, reg.get_int(db, "otp.max_attempts") - ch.attempts)})
    ch.consumed_at = now
    return ch


# ───────────────────────── tokens ─────────────────────────

def _issue_tokens(db: Session, subject_type: str, subject_id: int, request: Request | None,
                  family_id: str | None = None, extra: dict[str, Any] | None = None) -> TokenPair:
    s = get_settings()
    raw, digest = security.new_refresh_token()
    db.add(RefreshToken(subject_type=subject_type, subject_id=subject_id, token_hash=digest,
                        family_id=family_id or uuid.uuid4().hex, expires_at=clock.now() + timedelta(days=s.refresh_token_days),
                        ip=audit.client_ip(request) if request else None,
                        user_agent=(request.headers.get("user-agent") or "")[:300] if request else None))
    db.flush()
    access = security.issue_access_token(subject_type, subject_id, extra)  # type: ignore[arg-type]
    return TokenPair(access, raw, s.access_token_minutes * 60, subject_type, subject_id)


def refresh(db: Session, raw_token: str | None, request: Request | None) -> TokenPair:
    if not raw_token:
        raise AppError("not_authenticated", "نشست شما منقضی شده است؛ دوباره وارد شوید.", 401)
    rt = db.scalar(select(RefreshToken).where(RefreshToken.token_hash == security.sha256_hex(raw_token)))
    now = clock.now()
    if rt is None:
        raise AppError("not_authenticated", "نشست شما منقضی شده است؛ دوباره وارد شوید.", 401)
    if rt.revoked_at is not None:
        # Reuse of a rotated token = likely theft → kill the whole family.
        for t in db.scalars(select(RefreshToken).where(RefreshToken.family_id == rt.family_id, RefreshToken.revoked_at.is_(None))):
            t.revoked_at = now
        audit.record(db, audit.Actor(rt.subject_type, rt.subject_id), "auth.refresh_reuse", "refresh_token", rt.family_id, request=request)
        db.commit()
        raise AppError("not_authenticated", "نشست شما منقضی شده است؛ دوباره وارد شوید.", 401)
    if rt.expires_at <= now:
        raise AppError("not_authenticated", "نشست شما منقضی شده است؛ دوباره وارد شوید.", 401)
    if rt.subject_type == "staff":
        st = db.get(StaffUser, rt.subject_id)
        if st is None or not st.is_active:
            raise AppError("not_authenticated", "حساب کاربری غیرفعال است.", 401)
    else:
        u = db.get(User, rt.subject_id)
        if u is None or u.status != "active":
            raise AppError("not_authenticated", "حساب کاربری غیرفعال است.", 401)
    pair = _issue_tokens(db, rt.subject_type, rt.subject_id, request, family_id=rt.family_id)
    rt.revoked_at = now
    rt.replaced_by_id = db.scalar(select(RefreshToken.id).where(RefreshToken.token_hash == security.sha256_hex(pair.refresh_token)))
    return pair


def logout(db: Session, raw_token: str | None) -> None:
    if not raw_token:
        return
    rt = db.scalar(select(RefreshToken).where(RefreshToken.token_hash == security.sha256_hex(raw_token)))
    if rt is not None and rt.revoked_at is None:
        rt.revoked_at = clock.now()


def revoke_all(db: Session, subject_type: str, subject_id: int) -> None:
    for t in db.scalars(select(RefreshToken).where(RefreshToken.subject_type == subject_type,
                                                   RefreshToken.subject_id == subject_id, RefreshToken.revoked_at.is_(None))):
        t.revoked_at = clock.now()


# ───────────────────────── subscriber signup ─────────────────────────

def _bad_input() -> AppError:
    return AppError("not_eligible", NOT_ELIGIBLE_FA, 422)


def signup_start(db: Session, *, mobile_raw: str, subscription_raw: str, referral_code: str | None,
                 device_id: str | None, request: Request) -> dict[str, Any]:
    ip = audit.client_ip(request)
    mobile = normalize_mobile(mobile_raw)
    sub_no = normalize_subscription(subscription_raw)
    if mobile is None:
        raise AppError("validation_error", "شمارهٔ موبایل معتبر نیست.", 422, {"fields": {"mobile": "شمارهٔ موبایل معتبر نیست."}})
    if sub_no is None:
        raise AppError("validation_error", "شمارهٔ اشتراک معتبر نیست.", 422,
                       {"fields": {"subscription_no": "شمارهٔ اشتراک معتبر نیست."}})
    subscriber = subscribers.find_match(db, sub_no, mobile)
    eligible = subscribers.is_eligible(db, subscriber)
    # Decoy challenge on the ineligible path: same DB writes + same rate-limit accounting.
    result = _issue_otp(db, mobile=mobile, purpose="signup", ip=ip, decoy=not eligible,
                        context={"subscriber_id": subscriber.id if (subscriber and eligible) else None,
                                 "referral_code": (referral_code or "").strip().upper()[:12] or None,
                                 "device_id": (device_id or "")[:64] or None})
    audit.login_event(db, actor_type="user", actor_id=None, identifier_masked=mask_mobile(mobile), success=eligible,
                      reason="signup_start" if eligible else "signup_not_eligible", request=request)
    if not eligible:
        db.commit()  # keep the decoy + log, then answer with the exact R09 text
        raise _bad_input()
    return result


def signup_verify(db: Session, *, challenge_id: str, code: str, request: Request) -> dict[str, Any]:
    ch = _consume_otp(db, challenge_id, code, "signup")
    sid = ch.context.get("subscriber_id")
    if not sid:
        raise AppError("otp_expired", OTP_EXPIRED_FA, 400)
    existing = db.scalar(select(User).where(User.subscriber_id == sid))
    if existing is not None:
        if existing.status != "active":
            raise AppError("account_suspended", "حساب کاربری شما معلق شده است؛ با پشتیبانی تماس بگیرید.", 403)
        _touch_device(db, existing, ch.context.get("device_id"), request)
        pair = _issue_tokens(db, "user", existing.id, request)
        audit.login_event(db, actor_type="user", actor_id=existing.id, identifier_masked="otp", success=True,
                          reason="signup_existing_login", request=request)
        return {"status": "logged_in", "tokens": pair}
    token = security.issue_purpose_token("signup", {"sid": sid, "mb": ch.mobile_bidx, "ch": ch.id,
                                                    "ref": ch.context.get("referral_code"), "dev": ch.context.get("device_id")},
                                         get_settings().signup_token_minutes)
    return {"status": "verified", "signup_token": token, "terms_version": str(reg.get(db, "terms.version"))}


def _new_referral_code(db: Session) -> str:
    for _ in range(20):
        code = "".join(secrets.choice(REFERRAL_ALPHABET) for _ in range(7))
        if db.scalar(select(User.id).where(User.referral_code == code)) is None:
            return code
    raise RuntimeError("could not allocate referral code")


def _touch_device(db: Session, user: User, device_id: str | None, request: Request | None) -> None:
    if not device_id:
        return
    device_id = device_id[:64]
    d = db.scalar(select(UserDevice).where(UserDevice.user_id == user.id, UserDevice.device_id == device_id))
    ua = (request.headers.get("user-agent") or "")[:300] if request else None
    if d is None:
        db.add(UserDevice(user_id=user.id, device_id=device_id, user_agent=ua, last_seen_at=clock.now()))
    else:
        d.last_seen_at, d.user_agent = clock.now(), ua


def signup_complete(db: Session, *, signup_token: str, accept_terms: bool, accept_privacy: bool, login_method: str,
                    password: str | None, first_name: str | None, last_name: str | None, device_id: str | None,
                    request: Request) -> tuple[User, TokenPair]:
    from app.modules.points import service as points
    from app.modules.referrals import service as referrals
    from app.modules.subscribers.models import Subscriber

    try:
        claims = security.decode_token(signup_token, "signup")
    except jwt.PyJWTError as e:
        raise AppError("signup_expired", "مهلت تکمیل ثبت‌نام تمام شده است؛ دوباره شروع کنید.", 400) from e
    if not (accept_terms and accept_privacy):
        raise AppError("terms_required", "برای ادامه باید شرایط طرح و سیاست حریم خصوصی را بپذیرید.", 422)
    if login_method not in ("otp", "password"):
        raise AppError("validation_error", "روش ورود معتبر نیست.", 422)
    if login_method == "password":
        problem = password_problem(password or "")
        if problem:
            raise AppError("validation_error", problem, 422, {"fields": {"password": problem}})
    sid = int(claims["sid"])
    sub = db.get(Subscriber, sid)
    if sub is None or not subscribers.is_eligible(db, sub):
        raise _bad_input()
    if db.scalar(select(User.id).where(User.subscriber_id == sid)) is not None:
        raise AppError("already_registered", "این اشتراک قبلاً ثبت‌نام شده است؛ وارد شوید.", 409)
    if db.scalar(select(User.id).where(User.mobile_bidx == claims["mb"])) is not None:
        raise AppError("mobile_in_use", "این شمارهٔ موبایل برای حساب دیگری ثبت شده است؛ با پشتیبانی تماس بگیرید.", 409)
    mobile = crypto.decrypt(sub.mobile_enc) or ""
    now = clock.now()
    user = User(subscriber_id=sid, mobile_enc=crypto.encrypt(mobile) or "", mobile_bidx=claims["mb"],
                first_name=(first_name or "").strip()[:80] or None, last_name=(last_name or "").strip()[:80] or None,
                password_hash=security.hash_password(password) if login_method == "password" and password else None,
                login_method=login_method, terms_version=str(reg.get(db, "terms.version")), terms_accepted_at=now,
                privacy_accepted_at=now, referral_code=_new_referral_code(db))
    db.add(user)
    db.flush()
    dev = device_id or claims.get("dev")
    _touch_device(db, user, dev, request)
    db.flush()
    referrals.register(db, referee=user, code=claims.get("ref"), device_id=dev)
    # R11: exactly once, after full confirmation. Keyed by SUBSCRIBER so a deleted+recreated account cannot re-earn it.
    points.award(db, user_id=user.id, event_type="signup", idempotency_key=f"signup:subscriber:{sid}",
                 ref_type="user", ref_id=user.id)
    audit.record(db, audit.Actor("user", user.id), "user.signup", "user", user.id, None,
                 {"subscriber_id": sid, "login_method": login_method}, request)
    audit.login_event(db, actor_type="user", actor_id=user.id, identifier_masked=mask_mobile(mobile), success=True,
                      reason="signup_complete", request=request)
    return user, _issue_tokens(db, "user", user.id, request)


# ───────────────────────── subscriber login ─────────────────────────

def login_otp_start(db: Session, *, mobile_raw: str, request: Request) -> dict[str, Any]:
    mobile = normalize_mobile(mobile_raw)
    if mobile is None:
        raise AppError("validation_error", "شمارهٔ موبایل معتبر نیست.", 422, {"fields": {"mobile": "شمارهٔ موبایل معتبر نیست."}})
    user = db.scalar(select(User).where(User.mobile_bidx == crypto.blind_index(mobile, purpose="mobile")))
    real = user is not None and user.status == "active"
    # Unknown numbers get a decoy challenge: identical response, never verifiable, no SMS.
    return _issue_otp(db, mobile=mobile, purpose="login", ip=audit.client_ip(request), decoy=not real,
                      context={"user_id": user.id if real and user else None})


def login_otp_verify(db: Session, *, challenge_id: str, code: str, device_id: str | None, request: Request) -> TokenPair:
    ch = _consume_otp(db, challenge_id, code, "login")
    uid = ch.context.get("user_id")
    user = db.get(User, uid) if uid else None
    if user is None or user.status != "active":
        raise AppError("otp_wrong", OTP_WRONG_FA, 400)
    user.failed_logins, user.locked_until = 0, None
    _touch_device(db, user, device_id, request)
    audit.login_event(db, actor_type="user", actor_id=user.id, identifier_masked="otp", success=True, reason="otp", request=request)
    return _issue_tokens(db, "user", user.id, request)


def login_password(db: Session, *, mobile_raw: str, password: str, device_id: str | None, request: Request) -> TokenPair:
    ip = audit.client_ip(request)
    ratelimit.enforce(f"login:ip:{ip}", 30, 600)
    mobile = normalize_mobile(mobile_raw) or ""
    user = db.scalar(select(User).where(User.mobile_bidx == crypto.blind_index(mobile, purpose="mobile"))) if mobile else None
    now = clock.now()
    wrong = AppError("invalid_credentials", "شمارهٔ موبایل یا رمز عبور نادرست است.", 401)
    if user is not None and user.locked_until and user.locked_until > now:
        security.verify_password(password, None)
        raise AppError("account_locked", "به دلیل تلاش‌های ناموفق، ورود با رمز موقتاً غیرفعال است؛ با کد یک‌بارمصرف وارد شوید.", 423)
    ok = security.verify_password(password, user.password_hash if user else None)
    if not ok or user is None or user.status != "active":
        if user is not None:
            user.failed_logins += 1
            if user.failed_logins >= reg.get_int(db, "security.user_max_failed_logins"):
                user.locked_until = now + timedelta(minutes=reg.get_int(db, "security.staff_lock_minutes"))
        audit.login_event(db, actor_type="user", actor_id=user.id if user else None, identifier_masked=mask_mobile(mobile),
                          success=False, reason="bad_password", request=request)
        db.commit()
        raise wrong
    user.failed_logins, user.locked_until = 0, None
    _touch_device(db, user, device_id, request)
    audit.login_event(db, actor_type="user", actor_id=user.id, identifier_masked=mask_mobile(mobile), success=True,
                      reason="password", request=request)
    return _issue_tokens(db, "user", user.id, request)


# ───────────────────────── staff ─────────────────────────

def staff_login(db: Session, *, username: str, password: str, request: Request) -> dict[str, Any]:
    ip = audit.client_ip(request)
    ratelimit.enforce(f"staff_login:ip:{ip}", 30, 600)
    uname = username.strip().lower()
    ratelimit.enforce(f"staff_login:u:{uname}", 20, 600)
    st = db.scalar(select(StaffUser).where(StaffUser.username == uname))
    now = clock.now()
    if st is not None and st.locked_until and st.locked_until > now:
        security.verify_password(password, None)
        audit.login_event(db, actor_type="staff", actor_id=st.id, identifier_masked=uname, success=False, reason="locked", request=request)
        db.commit()
        mins = max(1, int((st.locked_until - now).total_seconds() // 60) + 1)
        raise AppError("account_locked", f"حساب به‌طور موقت قفل شده است؛ {mins} دقیقهٔ دیگر تلاش کنید.", 423)
    ok = security.verify_password(password, st.password_hash if st else None)
    if not ok or st is None or not st.is_active:
        if st is not None:
            st.failed_logins += 1
            if st.failed_logins >= reg.get_int(db, "security.staff_max_failed_logins"):
                st.locked_until = now + timedelta(minutes=reg.get_int(db, "security.staff_lock_minutes"))
        audit.login_event(db, actor_type="staff", actor_id=st.id if st else None, identifier_masked=uname[:64],
                          success=False, reason="bad_password" if st else "unknown_user", request=request)
        db.commit()
        raise AppError("invalid_credentials", "نام کاربری یا رمز عبور نادرست است.", 401)
    st.failed_logins, st.locked_until = 0, None
    if st.otp_2fa_enabled and st.mobile_enc:
        mobile = crypto.decrypt(st.mobile_enc) or ""
        ch = _issue_otp(db, mobile=mobile, purpose="staff_2fa", ip=ip, decoy=False, context={"staff_id": st.id})
        return {"otp_required": True, **ch}
    return {"otp_required": False, "tokens": _finish_staff_login(db, st, request)}


def staff_login_verify(db: Session, *, challenge_id: str, code: str, request: Request) -> TokenPair:
    ch = _consume_otp(db, challenge_id, code, "staff_2fa")
    st = db.get(StaffUser, ch.context.get("staff_id"))
    if st is None or not st.is_active:
        raise AppError("otp_wrong", OTP_WRONG_FA, 400)
    return _finish_staff_login(db, st, request)


def _finish_staff_login(db: Session, st: StaffUser, request: Request) -> TokenPair:
    st.last_login_at = clock.now()
    if security.needs_rehash(st.password_hash):
        pass  # rehash happens on next password change; argon2 params are stable
    audit.login_event(db, actor_type="staff", actor_id=st.id, identifier_masked=st.username, success=True,
                      reason="password", request=request)
    return _issue_tokens(db, "staff", st.id, request, extra={"roles": list(st.roles or [])})


def staff_profile(st: StaffUser) -> dict[str, Any]:
    perms = sorted(str(p) for p in permissions_for(st.roles or []))
    return {"id": st.id, "username": st.username, "full_name": st.full_name, "roles": list(st.roles or []),
            "permissions": perms, "must_change_password": st.must_change_password,
            "service_region_ids": list(st.service_region_ids or []), "otp_2fa_enabled": st.otp_2fa_enabled}


def change_staff_password(db: Session, st: StaffUser, current: str, new: str, request: Request) -> None:
    if not security.verify_password(current, st.password_hash):
        raise AppError("invalid_credentials", "رمز فعلی نادرست است.", 400)
    problem = password_problem(new)
    if problem:
        raise AppError("validation_error", problem, 422, {"fields": {"new_password": problem}})
    st.password_hash = security.hash_password(new)
    st.must_change_password = False
    revoke_all(db, "staff", st.id)
    audit.record(db, audit.Actor("staff", st.id), "staff.change_password", "staff", st.id, request=request)
