from __future__ import annotations

from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select

from app.core.deps import DB, StaffCtx, require
from app.core.pagination import Page, PageParams, page_params, paginate
from app.core.rbac import P
from app.modules.audit.models import AuditLog, LoginEvent
from app.modules.audit.schemas import AuditOut, LoginEventOut
from app.modules.staff.models import StaffUser

router = APIRouter(prefix="/audit", tags=["admin:audit"])


@router.get("/logs", response_model=Page[AuditOut])
def logs(db: DB, p: PageParams = Depends(page_params), actor_type: str | None = None, actor_id: int | None = None,
         action: Annotated[str | None, Query(max_length=64)] = None, entity_type: str | None = None,
         entity_id: str | None = None, date_from: datetime | None = None, date_to: datetime | None = None,
         _s: StaffCtx = require(P.AUDIT_VIEW)) -> Page[AuditOut]:
    stmt = select(AuditLog).order_by(AuditLog.id.desc())
    if actor_type:
        stmt = stmt.where(AuditLog.actor_type == actor_type)
    if actor_id:
        stmt = stmt.where(AuditLog.actor_id == actor_id)
    if action:
        stmt = stmt.where(AuditLog.action.startswith(action))
    if entity_type:
        stmt = stmt.where(AuditLog.entity_type == entity_type)
    if entity_id:
        stmt = stmt.where(AuditLog.entity_id == entity_id)
    if date_from:
        stmt = stmt.where(AuditLog.created_at >= date_from)
    if date_to:
        stmt = stmt.where(AuditLog.created_at < date_to)
    rows, total = paginate(db, stmt, p)
    staff_ids = {r.actor_id for r in rows if r.actor_type == "staff" and r.actor_id}
    names = dict(db.execute(select(StaffUser.id, StaffUser.full_name).where(StaffUser.id.in_(staff_ids))).all()) if staff_ids else {}
    items = []
    for r in rows:
        o = AuditOut.model_validate(r, from_attributes=True)
        o.actor_name = names.get(r.actor_id) if r.actor_type == "staff" else None
        items.append(o)
    return Page(items=items, total=total, page=p.page, size=p.size)


@router.get("/logins", response_model=Page[LoginEventOut])
def logins(db: DB, p: PageParams = Depends(page_params), actor_type: str | None = None, success: bool | None = None,
           actor_id: int | None = None, _s: StaffCtx = require(P.AUDIT_VIEW)) -> Page[LoginEventOut]:
    stmt = select(LoginEvent).order_by(LoginEvent.id.desc())
    if actor_type:
        stmt = stmt.where(LoginEvent.actor_type == actor_type)
    if success is not None:
        stmt = stmt.where(LoginEvent.success == success)
    if actor_id:
        stmt = stmt.where(LoginEvent.actor_id == actor_id)
    rows, total = paginate(db, stmt, p)
    return Page(items=[LoginEventOut.model_validate(r, from_attributes=True) for r in rows], total=total, page=p.page, size=p.size)
