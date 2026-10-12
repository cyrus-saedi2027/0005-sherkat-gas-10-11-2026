from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy import func, or_, select

from app.core import crypto
from app.core.deps import DB, StaffCtx, require
from app.core.errors import AppError
from app.core.normalize import normalize_mobile, normalize_subscription, normalize_text
from app.core.pagination import Page, PageParams, page_params
from app.core.rbac import P
from app.modules.regions.models import Region
from app.modules.regions.service import descendants
from app.modules.subscribers.models import Subscriber
from app.modules.users import service
from app.modules.users.models import User
from app.modules.users.schemas import AdminUserDetail, AdminUserOut, SuspendUserIn

router = APIRouter(prefix="/users", tags=["admin:users"])


@router.get("", response_model=Page[AdminUserOut])
def list_users(db: DB, p: PageParams = Depends(page_params), q: Annotated[str | None, Query(max_length=40)] = None,
               region_id: int | None = None, status: Annotated[str | None, Query(pattern="^(active|suspended)$")] = None,
               tier: Annotated[str | None, Query(pattern="^(no_cost|low_cost|high_cost|none)$")] = None,
               _s: StaffCtx = require(P.USERS_VIEW)) -> Page[AdminUserOut]:
    stmt = (select(User, Subscriber, Region).join(Subscriber, Subscriber.id == User.subscriber_id)
            .outerjoin(Region, Region.id == Subscriber.region_id).order_by(User.id.desc()))
    if q:
        m = normalize_mobile(q)
        sn = normalize_subscription(q)
        conds = []
        if m:
            conds.append(User.mobile_bidx == crypto.blind_index(m, purpose="mobile"))
        if sn:
            conds.append(Subscriber.subscription_no.startswith(sn))
        t = normalize_text(q)
        conds += [User.first_name.ilike(f"%{t}%"), User.last_name.ilike(f"%{t}%"), Subscriber.full_name.ilike(f"%{t}%")]
        stmt = stmt.where(or_(*conds))
    if region_id:
        stmt = stmt.where(Subscriber.region_id.in_(descendants(db, region_id)))
    if status:
        stmt = stmt.where(User.status == status)
    if tier:
        stmt = stmt.where(User.tier.is_(None) if tier == "none" else User.tier == tier)
    total = int(db.scalar(select(func.count()).select_from(stmt.order_by(None).subquery())) or 0)
    rows = db.execute(stmt.limit(p.size).offset(p.offset)).all()
    return Page(items=[service.admin_out(db, u, s, r) for u, s, r in rows], total=total, page=p.page, size=p.size)


@router.get("/{user_id}", response_model=AdminUserDetail)
def detail(user_id: int, db: DB, _s: StaffCtx = require(P.USERS_VIEW)) -> AdminUserDetail:
    u = db.get(User, user_id)
    if u is None:
        raise AppError("not_found", "کاربر پیدا نشد.", 404)
    return service.admin_detail(db, u)


@router.post("/{user_id}/status", response_model=AdminUserDetail)
def set_status(user_id: int, body: SuspendUserIn, request: Request, db: DB,
               staff: StaffCtx = require(P.USERS_SUSPEND)) -> AdminUserDetail:
    u = db.get(User, user_id)
    if u is None:
        raise AppError("not_found", "کاربر پیدا نشد.", 404)
    service.set_status(db, u, body.suspend, body.reason, staff.actor, request)
    return service.admin_detail(db, u)
