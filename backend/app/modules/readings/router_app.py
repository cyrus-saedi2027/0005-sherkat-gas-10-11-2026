from __future__ import annotations

from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, Request, UploadFile
from sqlalchemy import select

from app.core import clock, jalali
from app.core import settings_registry as reg
from app.core.deps import DB, CurrentUser
from app.core.errors import AppError
from app.core.normalize import to_ascii_digits
from app.core.pagination import Page, PageParams, page_params, paginate
from app.modules.readings import presenter, service
from app.modules.readings.models import MeterReading
from app.modules.readings.schemas import CurrentPeriodOut, ReadingDetailOut, ReadingOut
from app.modules.users.models import User

router = APIRouter(prefix="/readings", tags=["app:readings"])


@router.get("/current", response_model=CurrentPeriodOut)
def current_period(user: CurrentUser, db: DB) -> CurrentPeriodOut:
    months = int(reg.get(db, "reading.period_months"))
    pk = jalali.period_key(clock.now(), months)
    r = service.current(db, user.subscriber_id, pk)
    kind = None
    if r is None:
        kind = "initial"
    elif r.status == "needs_correction":
        kind = "correction"
    elif r.status in ("approved", "rejected"):
        kind = "review_request"
    return CurrentPeriodOut(period_key=pk, period_label=jalali.period_label(pk),
                            reading=presenter.reading_out(r) if r else None, can_submit=kind is not None,
                            submit_kind=kind, photo_required=bool(reg.get(db, "reading.photo_required")),
                            max_back_days=reg.get_int(db, "reading.max_back_days"))


@router.post("", response_model=ReadingOut, status_code=201)
async def submit(user: CurrentUser, db: DB, request: Request,
                 declared_value: Annotated[str, Form(max_length=20)],
                 reading_date: Annotated[date, Form()],
                 photo: Annotated[UploadFile | None, File()] = None,
                 user_note: Annotated[str | None, Form(max_length=500)] = None) -> ReadingOut:
    try:
        value = float(to_ascii_digits(declared_value).replace("٫", ".").replace(",", ""))
    except ValueError as e:
        raise AppError("validation_error", "عدد کنتور معتبر نیست.", 422, {"fields": {"declared_value": "یک عدد معتبر وارد کنید."}}) from e
    raw = None
    if photo is not None and photo.filename:
        # Read at most limit+1 bytes: the size check must not require buffering an unbounded body.
        limit = reg.get_int(db, "uploads.max_mb") * 1024 * 1024
        raw = await photo.read(limit + 1)
    u = db.get(User, user.id)
    assert u is not None
    r = service.submit(db, user=u, declared_value=value, reading_date=reading_date, photo=raw,
                       photo_name=photo.filename if photo else None, user_note=user_note, request=request)
    return presenter.reading_out(r)


@router.get("", response_model=Page[ReadingOut])
def my_readings(user: CurrentUser, db: DB, p: PageParams = Depends(page_params), all_revisions: bool = False) -> Page[ReadingOut]:
    stmt = select(MeterReading).where(MeterReading.user_id == user.id)
    if not all_revisions:
        stmt = stmt.where(MeterReading.is_current.is_(True))
    stmt = stmt.order_by(MeterReading.period_key.desc(), MeterReading.revision.desc())
    rows, total = paginate(db, stmt, p)
    return Page(items=[presenter.reading_out(r) for r in rows], total=total, page=p.page, size=p.size)


@router.get("/{reading_id}", response_model=ReadingDetailOut)
def my_reading(reading_id: int, user: CurrentUser, db: DB) -> ReadingDetailOut:
    r = db.get(MeterReading, reading_id)
    if r is None or r.user_id != user.id:
        raise AppError("not_found", "قرائت پیدا نشد.", 404)
    revs = presenter.revisions(db, r)
    return ReadingDetailOut(**presenter.reading_out(r).model_dump(),
                            events=presenter.events_out(db, [x.id for x in revs], for_staff=False),
                            revisions=[presenter.reading_out(x) for x in revs])
