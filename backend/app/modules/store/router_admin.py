from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, File, Request, UploadFile
from sqlalchemy import select

from app.core import audit
from app.core.deps import DB, StaffCtx, require
from app.core.errors import AppError
from app.core.rbac import P
from app.modules.files import service as files
from app.modules.store import service
from app.modules.store.models import RewardCategory, RewardItem
from app.modules.store.router_app import item_out
from app.modules.store.schemas import CategoryOut, ItemIn, ItemOut

router = APIRouter(prefix="/store", tags=["admin:store"])


@router.get("/categories", response_model=list[CategoryOut])
def categories(db: DB, _s: StaffCtx = require(P.REWARDS_VIEW)) -> list[CategoryOut]:
    service.seed_categories(db)
    return [CategoryOut.model_validate(c, from_attributes=True)
            for c in db.scalars(select(RewardCategory).order_by(RewardCategory.sort)).all()]


@router.get("/items", response_model=list[ItemOut])
def items(db: DB, _s: StaffCtx = require(P.REWARDS_VIEW)) -> list[ItemOut]:
    keys = {c.id: c.key for c in db.scalars(select(RewardCategory)).all()}
    return [item_out(i, keys) for i in db.scalars(select(RewardItem).order_by(RewardItem.sort, RewardItem.id)).all()]


@router.post("/images", status_code=201)
async def upload(db: DB, file: Annotated[UploadFile, File()], staff: StaffCtx = require(P.REWARDS_MANAGE)) -> dict[str, str | None]:
    f = files.save_image(db, await file.read(20 * 1024 * 1024 + 1), purpose="reward_image", owner_type="staff",
                         owner_id=staff.id, original_name=file.filename)
    return {"file_id": f.id, "url": files.url(f.id)}


def _apply(db, i: RewardItem, body: ItemIn) -> None:
    if db.get(RewardCategory, body.category_id) is None:
        raise AppError("not_found", "دسته پیدا نشد.", 404)
    if body.kind == "donation" and not body.charity_name:
        raise AppError("validation_error", "نام خیریه را وارد کنید.", 422, {"fields": {"charity_name": "الزامی است."}})
    for k, v in body.model_dump().items():
        setattr(i, k, v)


@router.post("/items", response_model=ItemOut, status_code=201)
def create(body: ItemIn, request: Request, db: DB, staff: StaffCtx = require(P.REWARDS_MANAGE)) -> ItemOut:
    i = RewardItem(category_id=body.category_id, title=body.title, kind=body.kind, points_cost=body.points_cost)
    _apply(db, i, body)
    db.add(i)
    db.flush()
    audit.record(db, staff.actor, "store.item_create", "reward_item", i.id, None, body.model_dump(), request)
    return item_out(i, {c.id: c.key for c in db.scalars(select(RewardCategory)).all()})


@router.put("/items/{item_id}", response_model=ItemOut)
def update(item_id: int, body: ItemIn, request: Request, db: DB, staff: StaffCtx = require(P.REWARDS_MANAGE)) -> ItemOut:
    i = db.get(RewardItem, item_id)
    if i is None:
        raise AppError("not_found", "کالا پیدا نشد.", 404)
    before = {k: getattr(i, k) for k in body.model_dump()}
    _apply(db, i, body)
    audit.record(db, staff.actor, "store.item_update", "reward_item", i.id, before, body.model_dump(), request)
    return item_out(i, {c.id: c.key for c in db.scalars(select(RewardCategory)).all()})
