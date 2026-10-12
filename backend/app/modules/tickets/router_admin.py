from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, Query, Request, UploadFile
from sqlalchemy import func, or_, select

from app.core import clock
from app.core.deps import DB, StaffCtx, require
from app.core.errors import AppError
from app.core.pagination import Page, PageParams, page_params
from app.core.rbac import P
from app.modules.tickets import presenter, service
from app.modules.tickets.models import Ticket
from app.modules.tickets.router_app import _uploads
from app.modules.tickets.schemas import AdminTicketDetail, AdminTicketOut, TicketUpdateIn

router = APIRouter(prefix="/tickets", tags=["admin:tickets"])


def _scope(stmt, staff: StaffCtx):
    if "super_admin" in staff.roles:
        return stmt
    return stmt.where(or_(Ticket.assigned_unit.in_(service.staff_units(staff)), Ticket.assignee_staff_id == staff.id))


@router.get("", response_model=Page[AdminTicketOut])
def queue(db: DB, p: PageParams = Depends(page_params), status: Annotated[str | None, Query(max_length=20)] = None,
          priority: str | None = None, unit: str | None = None, mine: bool = False, follow_up_due: bool = False,
          q: Annotated[str | None, Query(max_length=40)] = None, staff: StaffCtx = require(P.TICKETS_VIEW)) -> Page[AdminTicketOut]:
    stmt = _scope(select(Ticket), staff)
    if status == "active":
        stmt = stmt.where(Ticket.status.not_in(("resolved", "closed")))
    elif status:
        stmt = stmt.where(Ticket.status == status)
    if priority:
        stmt = stmt.where(Ticket.priority == priority)
    if unit:
        stmt = stmt.where(Ticket.assigned_unit == unit)
    if mine:
        stmt = stmt.where(Ticket.assignee_staff_id == staff.id)
    if follow_up_due:
        stmt = stmt.where(Ticket.follow_up_at <= clock.now(), Ticket.status.not_in(("resolved", "closed")))
    if q:
        stmt = stmt.where(or_(Ticket.tracking_code.ilike(f"%{q.upper()}%"), Ticket.title.ilike(f"%{q}%")))
    # urgent first, then oldest customer activity first (who has waited longest)
    order = {"urgent": 0, "high": 1, "normal": 2, "low": 3}
    total = int(db.scalar(select(func.count()).select_from(stmt.subquery())) or 0)
    rows = list(db.scalars(stmt.order_by(Ticket.updated_at.desc()).limit(p.size).offset(p.offset)).all())
    rows.sort(key=lambda t: order.get(t.priority, 2))
    return Page(items=[presenter.admin_out(db, t) for t in rows], total=total, page=p.page, size=p.size)


def _load(db, ticket_id: int, staff: StaffCtx) -> Ticket:
    t = db.get(Ticket, ticket_id)
    if t is None or not service.can_see(staff, t):
        raise AppError("not_found", "تیکت پیدا نشد.", 404)
    return t


@router.get("/{ticket_id}", response_model=AdminTicketDetail)
def detail(ticket_id: int, db: DB, staff: StaffCtx = require(P.TICKETS_VIEW)) -> AdminTicketDetail:
    return presenter.admin_detail(db, _load(db, ticket_id, staff))


@router.post("/{ticket_id}/messages", response_model=AdminTicketDetail)
async def reply(ticket_id: int, request: Request, db: DB, body: Annotated[str, Form(min_length=1, max_length=5000)],
                internal: Annotated[bool, Form()] = False, set_status: Annotated[str | None, Form(max_length=20)] = None,
                files: Annotated[list[UploadFile] | None, File()] = None, kinds: Annotated[list[str] | None, Form()] = None,
                staff: StaffCtx = require(P.TICKETS_HANDLE)) -> AdminTicketDetail:
    if set_status and set_status not in ("open", "in_progress", "awaiting_customer", "answered", "resolved", "closed"):
        raise AppError("validation_error", "وضعیت معتبر نیست.", 422)
    t = _load(db, ticket_id, staff)
    service.staff_reply(db, t, staff, body, internal, await _uploads(files, kinds), set_status, request)
    return presenter.admin_detail(db, t)


@router.patch("/{ticket_id}", response_model=AdminTicketDetail)
def update(ticket_id: int, body: TicketUpdateIn, request: Request, db: DB,
           staff: StaffCtx = require(P.TICKETS_HANDLE)) -> AdminTicketDetail:
    t = service.update(db, _load(db, ticket_id, staff), staff, status=body.status, priority=body.priority, unit=body.unit,
                       assignee_id=body.assignee_id, clear_assignee=body.clear_assignee, follow_up_at=body.follow_up_at,
                       clear_follow_up=body.clear_follow_up, request=request)
    return presenter.admin_detail(db, t)
