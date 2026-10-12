from __future__ import annotations

from fastapi import APIRouter, Request
from sqlalchemy import select

from app.core import audit
from app.core.deps import DB, StaffCtx, require
from app.core.errors import AppError
from app.core.rbac import P
from app.modules.regions.models import Region
from app.modules.regions.schemas import RegionIn, RegionOut
from app.modules.regions.service import descendants

router = APIRouter(prefix="/regions", tags=["admin:regions"])


@router.get("", response_model=list[RegionOut])
def list_regions(db: DB, _s: StaffCtx = require(P.DASHBOARD_VIEW)) -> list[RegionOut]:
    return [RegionOut.model_validate(r, from_attributes=True) for r in db.scalars(select(Region).order_by(Region.id)).all()]


@router.post("", response_model=RegionOut, status_code=201)
def create(body: RegionIn, request: Request, db: DB, staff: StaffCtx = require(P.SUBSCRIBERS_EDIT)) -> RegionOut:
    if db.scalar(select(Region.id).where(Region.code == body.code)):
        raise AppError("code_taken", "این کد منطقه تکراری است.", 409)
    if body.parent_id and db.get(Region, body.parent_id) is None:
        raise AppError("not_found", "منطقهٔ والد پیدا نشد.", 404)
    r = Region(**body.model_dump())
    db.add(r)
    db.flush()
    audit.record(db, staff.actor, "region.create", "region", r.id, None, body.model_dump(), request)
    return RegionOut.model_validate(r, from_attributes=True)


@router.put("/{region_id}", response_model=RegionOut)
def update(region_id: int, body: RegionIn, request: Request, db: DB, staff: StaffCtx = require(P.SUBSCRIBERS_EDIT)) -> RegionOut:
    r = db.get(Region, region_id)
    if r is None:
        raise AppError("not_found", "منطقه پیدا نشد.", 404)
    if body.parent_id and body.parent_id in descendants(db, region_id):
        raise AppError("bad_parent", "منطقه نمی‌تواند زیرمجموعهٔ خودش باشد.", 422)
    dup = db.scalar(select(Region.id).where(Region.code == body.code, Region.id != region_id))
    if dup:
        raise AppError("code_taken", "این کد منطقه تکراری است.", 409)
    before = audit.snapshot(r, ["name", "code", "parent_id", "is_active"])
    for k, v in body.model_dump().items():
        setattr(r, k, v)
    audit.record(db, staff.actor, "region.update", "region", r.id, before, body.model_dump(), request)
    return RegionOut.model_validate(r, from_attributes=True)
