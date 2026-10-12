from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, Request, UploadFile
from sqlalchemy import select

from app.core.deps import DB, CurrentUser
from app.core.errors import AppError
from app.core.pagination import Page, PageParams, page_params, paginate
from app.modules.tickets import presenter, service
from app.modules.tickets.models import Ticket
from app.modules.tickets.schemas import RateIn, TicketDetail, TicketOut

router = APIRouter(prefix="/tickets", tags=["app:tickets"])
MAX = 20 * 1024 * 1024 + 1


async def _uploads(files: list[UploadFile] | None, kinds: list[str] | None) -> list[tuple[bytes, str | None, str]]:
    out = []
    for i, f in enumerate((files or [])[:5]):
        if f.filename:
            out.append((await f.read(MAX), f.filename, (kinds or [])[i] if kinds and i < len(kinds) else "other"))
    return out


@router.get("/subjects")
def subjects() -> list[dict[str, str]]:
    return [{"key": k, "title": v} for k, v in service.SUBJECTS.items()]


@router.post("", response_model=TicketDetail, status_code=201)
async def create(user: CurrentUser, request: Request, db: DB, subject_key: Annotated[str, Form(max_length=16)],
                 title: Annotated[str, Form(min_length=3, max_length=160)], body: Annotated[str, Form(min_length=3, max_length=5000)],
                 files: Annotated[list[UploadFile] | None, File()] = None,
                 kinds: Annotated[list[str] | None, Form()] = None) -> TicketDetail:
    t = service.create(db, user_id=user.id, subject_key=subject_key, title=title, body=body,
                       uploads=await _uploads(files, kinds), request=request)
    return presenter.user_detail(db, t)


@router.get("", response_model=Page[TicketOut])
def mine(user: CurrentUser, db: DB, p: PageParams = Depends(page_params)) -> Page[TicketOut]:
    rows, total = paginate(db, select(Ticket).where(Ticket.user_id == user.id).order_by(Ticket.updated_at.desc()), p)
    return Page(items=[presenter.ticket_out(t) for t in rows], total=total, page=p.page, size=p.size)


def _own(db, ticket_id: int, user_id: int) -> Ticket:
    t = db.get(Ticket, ticket_id)
    if t is None or t.user_id != user_id:
        raise AppError("not_found", "تیکت پیدا نشد.", 404)
    return t


@router.get("/{ticket_id}", response_model=TicketDetail)
def detail(ticket_id: int, user: CurrentUser, db: DB) -> TicketDetail:
    return presenter.user_detail(db, _own(db, ticket_id, user.id))


@router.post("/{ticket_id}/messages", response_model=TicketDetail)
async def reply(ticket_id: int, user: CurrentUser, request: Request, db: DB, body: Annotated[str, Form(min_length=1, max_length=5000)],
                files: Annotated[list[UploadFile] | None, File()] = None,
                kinds: Annotated[list[str] | None, Form()] = None) -> TicketDetail:
    t = _own(db, ticket_id, user.id)
    service.user_reply(db, t, user.id, body, await _uploads(files, kinds), request)
    return presenter.user_detail(db, t)


@router.post("/{ticket_id}/rate", response_model=TicketDetail)
def rate(ticket_id: int, body: RateIn, user: CurrentUser, db: DB) -> TicketDetail:
    t = service.rate(db, _own(db, ticket_id, user.id), user.id, body.rating, body.comment)
    return presenter.user_detail(db, t)
