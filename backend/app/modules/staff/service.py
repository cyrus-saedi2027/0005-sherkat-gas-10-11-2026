from __future__ import annotations

from fastapi import Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core import audit, clock, crypto, security
from app.core.errors import AppError
from app.core.normalize import mask_mobile, normalize_mobile
from app.core.validators import password_problem
from app.modules.staff.models import StaffUser
from app.modules.staff.schemas import StaffCreate, StaffOut, StaffUpdate

FIELDS = ["username", "full_name", "roles", "service_region_ids", "is_active", "otp_2fa_enabled"]


def to_out(st: StaffUser) -> StaffOut:
    mobile = crypto.decrypt(st.mobile_enc) if st.mobile_enc else None
    return StaffOut(id=st.id, username=st.username, full_name=st.full_name, mobile_masked=mask_mobile(mobile),
                    roles=list(st.roles or []), service_region_ids=list(st.service_region_ids or []),
                    is_active=st.is_active, otp_2fa_enabled=st.otp_2fa_enabled,
                    locked=bool(st.locked_until and st.locked_until > clock.now()), last_login_at=st.last_login_at,
                    access_reviewed_at=st.access_reviewed_at, created_at=st.created_at)


def _mobile_fields(raw: str | None) -> tuple[str | None, str | None]:
    if not raw:
        return None, None
    m = normalize_mobile(raw)
    if m is None:
        raise AppError("validation_error", "شمارهٔ موبایل معتبر نیست.", 422, {"fields": {"mobile": "شمارهٔ موبایل معتبر نیست."}})
    return crypto.encrypt(m), crypto.blind_index(m, purpose="mobile")


def create(db: Session, body: StaffCreate, actor: audit.Actor, request: Request | None = None,
           must_change_password: bool = True) -> StaffUser:
    uname = body.username.strip().lower()
    if db.scalar(select(StaffUser.id).where(StaffUser.username == uname)):
        raise AppError("username_taken", "این نام کاربری قبلاً استفاده شده است.", 409, {"fields": {"username": "تکراری است."}})
    problem = password_problem(body.password)
    if problem:
        raise AppError("validation_error", problem, 422, {"fields": {"password": problem}})
    enc, bidx = _mobile_fields(body.mobile)
    if body.otp_2fa_enabled and not enc:
        raise AppError("validation_error", "برای ورود دومرحله‌ای شمارهٔ موبایل لازم است.", 422)
    st = StaffUser(username=uname, full_name=body.full_name.strip(), mobile_enc=enc, mobile_bidx=bidx,
                   password_hash=security.hash_password(body.password), roles=body.roles,
                   service_region_ids=body.service_region_ids, otp_2fa_enabled=body.otp_2fa_enabled,
                   must_change_password=must_change_password)
    db.add(st)
    db.flush()
    audit.record(db, actor, "staff.create", "staff", st.id, None, audit.snapshot(st, FIELDS), request)
    return st


def update(db: Session, st: StaffUser, body: StaffUpdate, actor: audit.Actor, request: Request | None = None) -> StaffUser:
    before = audit.snapshot(st, FIELDS)
    data = body.model_dump(exclude_unset=True)
    if actor.id == st.id and (data.get("is_active") is False or ("roles" in data and "super_admin" in st.roles
                                                                  and "super_admin" not in (data["roles"] or []))):
        raise AppError("self_lockout", "نمی‌توانید دسترسی مدیریتی خودتان را حذف یا حسابتان را غیرفعال کنید.", 409)
    if "mobile" in data:
        st.mobile_enc, st.mobile_bidx = _mobile_fields(data.pop("mobile"))
    for k, v in data.items():
        setattr(st, k, v)
    if st.otp_2fa_enabled and not st.mobile_enc:
        raise AppError("validation_error", "برای ورود دومرحله‌ای شمارهٔ موبایل لازم است.", 422)
    if data.get("is_active") is False or "roles" in data:
        from app.modules.auth.service import revoke_all

        revoke_all(db, "staff", st.id)  # role/active changes take effect on the next refresh too
    audit.record(db, actor, "staff.update", "staff", st.id, before, audit.snapshot(st, FIELDS), request)
    return st


def reset_password(db: Session, st: StaffUser, new_password: str, actor: audit.Actor, request: Request | None = None) -> None:
    problem = password_problem(new_password)
    if problem:
        raise AppError("validation_error", problem, 422, {"fields": {"new_password": problem}})
    st.password_hash = security.hash_password(new_password)
    st.must_change_password = True
    st.failed_logins, st.locked_until = 0, None
    from app.modules.auth.service import revoke_all

    revoke_all(db, "staff", st.id)
    audit.record(db, actor, "staff.reset_password", "staff", st.id, request=request)
