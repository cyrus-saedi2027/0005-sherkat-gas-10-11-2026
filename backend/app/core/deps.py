"""Request dependencies: DB session, authenticated subject, permission checks."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Annotated

import jwt
from fastapi import Depends, Request
from sqlalchemy.orm import Session

from app.core import audit, clock, ratelimit
from app.core import settings_registry as reg
from app.core.db import get_db
from app.core.errors import AppError
from app.core.rbac import P, permissions_for
from app.core.security import decode_token

# scope="function": the session commits right after the endpoint returns and
# BEFORE the response is sent — a client never sees 200 for data that failed to commit.
DB = Annotated[Session, Depends(get_db, scope="function")]


def _bearer(request: Request) -> str | None:
    h = request.headers.get("authorization", "")
    return h[7:].strip() if h.lower().startswith("bearer ") else None


def _claims(request: Request, expected_subject: str) -> dict:
    token = _bearer(request)
    if not token:
        raise AppError("not_authenticated", "ابتدا وارد حساب کاربری شوید.", 401)
    try:
        claims = decode_token(token, "access")
    except jwt.ExpiredSignatureError as e:
        raise AppError("token_expired", "نشست شما منقضی شده است.", 401) from e
    except jwt.InvalidTokenError as e:
        raise AppError("not_authenticated", "ابتدا وارد حساب کاربری شوید.", 401) from e
    if claims.get("st") != expected_subject:
        raise AppError("forbidden", "شما به این بخش دسترسی ندارید.", 403)
    return claims


@dataclass
class StaffCtx:
    id: int
    username: str
    full_name: str
    roles: tuple[str, ...]
    perms: frozenset[P]
    region_ids: tuple[int, ...] = field(default_factory=tuple)

    @property
    def actor(self) -> audit.Actor:
        return audit.Actor("staff", self.id, self.roles)

    def can(self, perm: P) -> bool:
        return perm in self.perms


@dataclass
class UserCtx:
    id: int
    subscriber_id: int

    @property
    def actor(self) -> audit.Actor:
        return audit.Actor("user", self.id)


def get_current_staff(request: Request, db: DB) -> StaffCtx:
    from app.modules.staff.models import StaffUser

    claims = _claims(request, "staff")
    staff = db.get(StaffUser, int(claims["sub"]))
    # Roles are re-read from the DB on every request: revoking a role takes effect
    # immediately, not when the 15-minute token expires (R35 access review).
    if staff is None or not staff.is_active:
        raise AppError("not_authenticated", "حساب کاربری غیرفعال است.", 401)
    ratelimit.enforce(f"api:staff:{staff.id}", reg.get_int(db, "security.api_per_minute") * 2, 60)
    ctx = StaffCtx(staff.id, staff.username, staff.full_name, tuple(staff.roles or ()),
                   permissions_for(staff.roles or []), tuple(staff.service_region_ids or ()))
    request.state.actor = ctx.actor
    return ctx


def get_current_user(request: Request, db: DB) -> UserCtx:
    from app.modules.users.models import User

    claims = _claims(request, "user")
    user = db.get(User, int(claims["sub"]))
    if user is None:
        raise AppError("not_authenticated", "ابتدا وارد حساب کاربری شوید.", 401)
    if user.status != "active":
        raise AppError("account_suspended", "حساب کاربری شما معلق شده است؛ با پشتیبانی تماس بگیرید.", 403)
    ratelimit.enforce(f"api:user:{user.id}", reg.get_int(db, "security.api_per_minute"), 60)
    now = clock.now()
    if user.last_seen_at is None or (now - user.last_seen_at).total_seconds() > 300:
        user.last_seen_at = now
    ctx = UserCtx(user.id, user.subscriber_id)
    request.state.actor = ctx.actor
    return ctx


CurrentStaff = Annotated[StaffCtx, Depends(get_current_staff)]
CurrentUser = Annotated[UserCtx, Depends(get_current_user)]


def require(*perms: P):
    """Endpoint guard: the staff member needs ALL listed permissions."""

    def _dep(staff: CurrentStaff) -> StaffCtx:
        missing = [p for p in perms if p not in staff.perms]
        if missing:
            raise AppError("forbidden", "شما به این بخش دسترسی ندارید.", 403, {"missing": [str(m) for m in missing]})
        return staff

    return Depends(_dep)


def require_any(*perms: P):
    def _dep(staff: CurrentStaff) -> StaffCtx:
        if not any(p in staff.perms for p in perms):
            raise AppError("forbidden", "شما به این بخش دسترسی ندارید.", 403)
        return staff

    return Depends(_dep)
