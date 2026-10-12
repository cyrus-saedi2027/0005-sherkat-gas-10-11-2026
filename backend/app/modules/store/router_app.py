from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from sqlalchemy import select

from app.core import settings_registry as reg
from app.core.deps import DB, CurrentUser
from app.core.errors import AppError
from app.core.pagination import Page, PageParams, page_params, paginate
from app.modules.files import service as files
from app.modules.points import service as points
from app.modules.store import service
from app.modules.store.models import Redemption, RewardCategory, RewardItem
from app.modules.store.schemas import CategoryOut, ItemOut, RedeemIn, RedemptionOut, StoreOut
from app.modules.users.models import User

router = APIRouter(prefix="/store", tags=["app:store"])


def item_out(i: RewardItem, cats: dict[int, str]) -> ItemOut:
    return ItemOut(id=i.id, category_id=i.category_id, category_key=cats.get(i.category_id), title=i.title,
                   description=i.description, image_url=files.url(i.image_file_id), kind=i.kind, points_cost=i.points_cost,
                   rial_value=i.rial_value, stock=i.stock, is_active=i.is_active, charity_name=i.charity_name,
                   needs_address=i.needs_address)


@router.get("", response_model=StoreOut)
def store(user: CurrentUser, db: DB) -> StoreOut:
    service.seed_categories(db)
    cats = db.scalars(select(RewardCategory).where(RewardCategory.is_active.is_(True)).order_by(RewardCategory.sort)).all()
    keys = {c.id: c.key for c in cats}
    items = db.scalars(select(RewardItem).where(RewardItem.is_active.is_(True)).order_by(RewardItem.sort, RewardItem.id)).all()
    b = points.balance(db, user.id)
    u = db.get(User, user.id)
    return StoreOut(categories=[CategoryOut.model_validate(c, from_attributes=True) for c in cats],
                    items=[item_out(i, keys) for i in items if i.category_id in keys], available_points=b.available,
                    pending_points=b.pending, rial_rate=reg.get_int(db, "finance.point_rial_rate"),
                    min_cash_points=reg.get_int(db, "finance.min_cash_withdraw_points"), has_iban=bool(u and u.iban_enc),
                    window_open=service._window_open(db))


@router.post("/redeem", response_model=RedemptionOut, status_code=201)
def redeem(body: RedeemIn, user: CurrentUser, request: Request, db: DB) -> RedemptionOut:
    u = db.get(User, user.id)
    assert u is not None
    r = service.redeem(db, user=u, item_id=body.item_id, kind="cash" if body.kind == "cash" else "item",
                       points_amount=body.points, delivery_address=body.delivery_address, note=body.note, request=request)
    return RedemptionOut.model_validate(r, from_attributes=True)


@router.get("/redemptions", response_model=Page[RedemptionOut])
def my_redemptions(user: CurrentUser, db: DB, p: PageParams = Depends(page_params)) -> Page[RedemptionOut]:
    rows, total = paginate(db, select(Redemption).where(Redemption.user_id == user.id).order_by(Redemption.id.desc()), p)
    return Page(items=[RedemptionOut.model_validate(r, from_attributes=True) for r in rows], total=total, page=p.page, size=p.size)


@router.post("/redemptions/{redemption_id}/cancel", response_model=RedemptionOut)
def cancel(redemption_id: int, user: CurrentUser, request: Request, db: DB) -> RedemptionOut:
    r = db.get(Redemption, redemption_id)
    if r is None:
        raise AppError("not_found", "درخواست پیدا نشد.", 404)
    return RedemptionOut.model_validate(service.cancel(db, r, user.id, request), from_attributes=True)
