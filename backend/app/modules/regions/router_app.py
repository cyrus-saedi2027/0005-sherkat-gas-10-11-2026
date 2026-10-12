from __future__ import annotations

from fastapi import APIRouter
from sqlalchemy import select

from app.core.deps import DB
from app.modules.regions.models import Region
from app.modules.regions.schemas import RegionOut

router = APIRouter(prefix="/regions", tags=["app:regions"])


@router.get("", response_model=list[RegionOut])
def list_regions(db: DB) -> list[RegionOut]:
    rows = db.scalars(select(Region).where(Region.is_active.is_(True)).order_by(Region.name)).all()
    return [RegionOut.model_validate(r, from_attributes=True) for r in rows]
