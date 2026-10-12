from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request, Response
from sqlalchemy import or_, select

from app.core import audit, clock
from app.core.deps import DB, StaffCtx, require
from app.core.errors import AppError
from app.core.normalize import normalize_text
from app.core.pagination import Page, PageParams, page_params, paginate
from app.core.rbac import ROLE_FA, ROLE_PERMISSIONS, P, Role
from app.modules.staff import service
from app.modules.staff.models import StaffUser
from app.modules.staff.schemas import (
    AccessReviewIn,
    ResetPasswordIn,
    RoleOut,
    StaffCreate,
    StaffOut,
    StaffUpdate,
)

router = APIRouter(prefix="/staff", tags=["admin:staff"])


@router.get("/roles", response_model=list[RoleOut])
def roles(_s: StaffCtx = require(P.STAFF_VIEW)) -> list[RoleOut]:
    return [RoleOut(id=r.value, title_fa=ROLE_FA[r], permissions=sorted(p.value for p in ROLE_PERMISSIONS[r])) for r in Role]


@router.get("", response_model=Page[StaffOut])
def list_staff(db: DB, p: PageParams = Depends(page_params), q: Annotated[str | None, Query(max_length=64)] = None,
               role: str | None = None, active: bool | None = None, _s: StaffCtx = require(P.STAFF_VIEW)) -> Page[StaffOut]:
    stmt = select(StaffUser).order_by(StaffUser.id)
    if q:
        t = f"%{normalize_text(q)}%"
        stmt = stmt.where(or_(StaffUser.username.ilike(t), StaffUser.full_name.ilike(t)))
    if active is not None:
        stmt = stmt.where(StaffUser.is_active == active)
    rows, total = paginate(db, stmt, p)
    items = [service.to_out(s) for s in rows]
    if role:  # JSON array filtering differs across DBs; the staff table is small
        items = [i for i in items if role in i.roles]
    return Page(items=items, total=total if not role else len(items), page=p.page, size=p.size)


@router.get("/ambassadors", response_model=list[StaffOut])
def ambassadors(db: DB, _s: StaffCtx = require(P.CASES_VIEW_ALL)) -> list[StaffOut]:
    rows = db.scalars(select(StaffUser).where(StaffUser.is_active.is_(True)).order_by(StaffUser.full_name)).all()
    return [service.to_out(s) for s in rows if "ambassador" in (s.roles or [])]


@router.post("", response_model=StaffOut, status_code=201)
def create(body: StaffCreate, request: Request, db: DB, staff: StaffCtx = require(P.STAFF_MANAGE)) -> StaffOut:
    return service.to_out(service.create(db, body, staff.actor, request))


@router.get("/{staff_id}", response_model=StaffOut)
def get_one(staff_id: int, db: DB, _s: StaffCtx = require(P.STAFF_VIEW)) -> StaffOut:
    st = db.get(StaffUser, staff_id)
    if st is None:
        raise AppError("not_found", "کاربر پیدا نشد.", 404)
    return service.to_out(st)


@router.patch("/{staff_id}", response_model=StaffOut)
def update(staff_id: int, body: StaffUpdate, request: Request, db: DB, staff: StaffCtx = require(P.STAFF_MANAGE)) -> StaffOut:
    st = db.get(StaffUser, staff_id)
    if st is None:
        raise AppError("not_found", "کاربر پیدا نشد.", 404)
    return service.to_out(service.update(db, st, body, staff.actor, request))


@router.post("/{staff_id}/reset-password", status_code=204)
def reset_password(staff_id: int, body: ResetPasswordIn, request: Request, db: DB,
                   staff: StaffCtx = require(P.STAFF_MANAGE)) -> Response:
    st = db.get(StaffUser, staff_id)
    if st is None:
        raise AppError("not_found", "کاربر پیدا نشد.", 404)
    service.reset_password(db, st, body.new_password, staff.actor, request)
    return Response(status_code=204)


@router.post("/access-review", status_code=204)
def access_review(body: AccessReviewIn, request: Request, db: DB, staff: StaffCtx = require(P.ACCESS_REVIEW_PERFORM)) -> Response:
    """Periodic access review (R35): stamps every active account as reviewed and snapshots roles into the audit log."""
    now = clock.now()
    snap = []
    for st in db.scalars(select(StaffUser).where(StaffUser.is_active.is_(True))).all():
        st.access_reviewed_at = now
        snap.append({"id": st.id, "username": st.username, "roles": st.roles, "last_login_at": st.last_login_at})
    audit.record(db, staff.actor, "staff.access_review", "staff", None, None, {"notes": body.notes, "accounts": snap}, request)
    return Response(status_code=204)
