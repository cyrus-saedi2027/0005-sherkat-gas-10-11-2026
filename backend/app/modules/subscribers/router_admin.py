from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, File, Query, Request, UploadFile
from fastapi.responses import Response
from sqlalchemy import func, or_, select

from app.core import audit, clock, crypto, storage
from app.core import settings_registry as reg
from app.core.deps import DB, StaffCtx, require
from app.core.errors import AppError
from app.core.normalize import mask_mobile, normalize_mobile, normalize_subscription, normalize_text
from app.core.pagination import Page, PageParams, page_params
from app.core.rbac import P
from app.modules.files import service as files
from app.modules.regions.models import Region
from app.modules.regions.service import descendants
from app.modules.subscribers import importer, service
from app.modules.subscribers.models import ImportBatch, Subscriber
from app.modules.subscribers.schemas import (
    CommitIn,
    HistoryYear,
    ImportBatchOut,
    SubscriberDetail,
    SubscriberOut,
    SubscriberUpdate,
)
from app.modules.users.models import User

router = APIRouter(prefix="/subscribers", tags=["admin:subscribers"])
XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


def _out(db, s: Subscriber, region: Region | None, user_id: int | None) -> SubscriberOut:
    return SubscriberOut(id=s.id, subscription_no=s.subscription_no, full_name=s.full_name,
                         mobile_masked=mask_mobile(crypto.decrypt(s.mobile_enc)), region_id=s.region_id,
                         region_name=region.name if region else None, meter_serial=s.meter_serial, is_active=s.is_active,
                         baseline_annual_m3=s.baseline_annual_m3, eligible=service.is_eligible(db, s),
                         registered=user_id is not None, user_id=user_id)


@router.get("", response_model=Page[SubscriberOut])
def list_subscribers(db: DB, p: PageParams = Depends(page_params), q: Annotated[str | None, Query(max_length=40)] = None,
                     region_id: int | None = None, registered: bool | None = None, active: bool | None = None,
                     _s: StaffCtx = require(P.SUBSCRIBERS_VIEW)) -> Page[SubscriberOut]:
    stmt = (select(Subscriber, Region, User.id).outerjoin(Region, Region.id == Subscriber.region_id)
            .outerjoin(User, User.subscriber_id == Subscriber.id).order_by(Subscriber.id))
    if q:
        conds = []
        if (sn := normalize_subscription(q)):
            conds.append(Subscriber.subscription_no.startswith(sn))
        if (m := normalize_mobile(q)):
            conds.append(Subscriber.mobile_bidx == service.mobile_bidx(m))
        conds.append(Subscriber.full_name.ilike(f"%{normalize_text(q)}%"))
        stmt = stmt.where(or_(*conds))
    if region_id:
        stmt = stmt.where(Subscriber.region_id.in_(descendants(db, region_id)))
    if registered is not None:
        stmt = stmt.where(User.id.is_not(None) if registered else User.id.is_(None))
    if active is not None:
        stmt = stmt.where(Subscriber.is_active == active)
    total = int(db.scalar(select(func.count()).select_from(stmt.order_by(None).subquery())) or 0)
    rows = db.execute(stmt.limit(p.size).offset(p.offset)).all()
    return Page(items=[_out(db, s, r, uid) for s, r, uid in rows], total=total, page=p.page, size=p.size)


@router.get("/import/template")
def import_template(_s: StaffCtx = require(P.SUBSCRIBERS_IMPORT)) -> Response:
    return Response(importer.template(), media_type=XLSX,
                    headers={"Content-Disposition": 'attachment; filename="gazyar-subscribers-template.xlsx"'})


@router.get("/import/batches", response_model=Page[ImportBatchOut])
def batches(db: DB, p: PageParams = Depends(page_params), _s: StaffCtx = require(P.SUBSCRIBERS_IMPORT)) -> Page[ImportBatchOut]:
    stmt = select(ImportBatch).order_by(ImportBatch.id.desc())
    total = int(db.scalar(select(func.count()).select_from(ImportBatch)) or 0)
    rows = db.scalars(stmt.limit(p.size).offset(p.offset)).all()
    return Page(items=[ImportBatchOut.model_validate(b, from_attributes=True) for b in rows], total=total, page=p.page, size=p.size)


@router.post("/import", response_model=ImportBatchOut, status_code=201)
async def upload_import(request: Request, db: DB, file: Annotated[UploadFile, File()],
                        staff: StaffCtx = require(P.SUBSCRIBERS_IMPORT)) -> ImportBatchOut:
    name = (file.filename or "import.xlsx")[:255]
    if not name.lower().endswith(".xlsx"):
        raise AppError("bad_file_type", "فقط فایل اکسل ‎.xlsx‎ پذیرفته می‌شود.", 415)
    raw = await file.read(20 * 1024 * 1024 + 1)
    if raw[:2] != b"PK":  # xlsx is a zip; reject renamed binaries early
        raise AppError("bad_file_type", "فایل ارسالی اکسل معتبر نیست.", 415)
    stored = files.save_document(db, raw, purpose="import_xlsx", owner_type="staff", owner_id=staff.id,
                                 original_name=name, mime=XLSX, max_bytes=20 * 1024 * 1024)
    parsed = importer.parse(raw, db)
    batch = ImportBatch(kind="combined", filename=name, file_id=stored.id, uploaded_by=staff.id, status="validated",
                        row_count=parsed.rows, error_count=len(parsed.errors), errors=parsed.errors,
                        summary=importer.summarize(db, parsed))
    db.add(batch)
    db.flush()
    audit.record(db, staff.actor, "subscribers.import_validate", "import_batch", batch.id, None, batch.summary, request)
    return ImportBatchOut.model_validate(batch, from_attributes=True)


@router.post("/import/{batch_id}/commit", response_model=ImportBatchOut)
def commit_import(batch_id: int, body: CommitIn, request: Request, db: DB,
                  staff: StaffCtx = require(P.SUBSCRIBERS_IMPORT)) -> ImportBatchOut:
    batch = db.get(ImportBatch, batch_id)
    if batch is None:
        raise AppError("not_found", "دستهٔ ورود اطلاعات پیدا نشد.", 404)
    if batch.status != "validated":
        raise AppError("bad_state", "این فایل قبلاً ثبت شده است.", 409)
    if batch.error_count and not body.skip_errors:
        raise AppError("has_errors", "فایل خطا دارد؛ یا خطاها را اصلاح کنید یا ثبتِ ردیف‌های سالم را انتخاب کنید.", 409)
    f = files.get(db, batch.file_id or "")
    if f is None:
        raise AppError("not_found", "فایل این دسته پیدا نشد.", 404)
    parsed = importer.parse(storage.read(f.storage_key), db)  # re-parse: data may have changed since validation
    result = importer.commit(db, parsed, batch)
    batch.status, batch.committed_at = "committed", clock.now()
    batch.summary = {**batch.summary, **result}
    audit.record(db, staff.actor, "subscribers.import_commit", "import_batch", batch.id, None, result, request)
    return ImportBatchOut.model_validate(batch, from_attributes=True)


@router.get("/{subscriber_id}", response_model=SubscriberDetail)
def detail(subscriber_id: int, db: DB, _s: StaffCtx = require(P.SUBSCRIBERS_VIEW)) -> SubscriberDetail:
    s = db.get(Subscriber, subscriber_id)
    if s is None:
        raise AppError("not_found", "مشترک پیدا نشد.", 404)
    region = db.get(Region, s.region_id) if s.region_id else None
    uid = db.scalar(select(User.id).where(User.subscriber_id == s.id))
    hist = service.history_series(db, s.id)
    base = {m: b for m in range(1, 13) if (b := service.monthly_baseline(db, s.id, m)) is not None}
    return SubscriberDetail(**_out(db, s, region, uid).model_dump(), address=s.address,
                            history=[HistoryYear(jyear=y, months=ms, total=round(sum(ms.values()), 2)) for y, ms in sorted(hist.items())],
                            monthly_baseline=base, threshold_m3=reg.get_int(db, "eligibility.threshold_m3"),
                            threshold_basis=str(reg.get(db, "eligibility.threshold_basis")),
                            eligibility_value=service.eligibility_value(db, s))


@router.patch("/{subscriber_id}", response_model=SubscriberDetail)
def update(subscriber_id: int, body: SubscriberUpdate, request: Request, db: DB,
           staff: StaffCtx = require(P.SUBSCRIBERS_EDIT)) -> SubscriberDetail:
    s = db.get(Subscriber, subscriber_id)
    if s is None:
        raise AppError("not_found", "مشترک پیدا نشد.", 404)
    fields = ["full_name", "address", "region_id", "meter_serial", "is_active"]
    before = audit.snapshot(s, fields)
    data = body.model_dump(exclude_unset=True)
    if "mobile" in data:
        m = normalize_mobile(data.pop("mobile") or "")
        if not m:
            raise AppError("validation_error", "شمارهٔ موبایل معتبر نیست.", 422, {"fields": {"mobile": "نامعتبر"}})
        s.mobile_enc, s.mobile_bidx = crypto.encrypt(m), service.mobile_bidx(m)
        before["mobile"], data["mobile_changed"] = "***", True
    if data.get("region_id") and db.get(Region, data["region_id"]) is None:
        raise AppError("not_found", "منطقه پیدا نشد.", 404)
    for k in fields:
        if k in data:
            setattr(s, k, data[k])
    audit.record(db, staff.actor, "subscriber.update", "subscriber", s.id, before, {**audit.snapshot(s, fields), **data}, request)
    return detail(subscriber_id, db, staff)
