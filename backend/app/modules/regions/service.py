from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.regions.models import Region


def descendants(db: Session, region_id: int) -> set[int]:
    """The region and every zone below it (filters "by region" must include its zones)."""
    out, frontier = {region_id}, [region_id]
    while frontier:
        kids = list(db.scalars(select(Region.id).where(Region.parent_id.in_(frontier))).all())
        kids = [k for k in kids if k not in out]
        out.update(kids)
        frontier = kids
    return out


def ancestors(db: Session, region_id: int | None) -> list[int]:
    out: list[int] = []
    seen: set[int] = set()
    while region_id is not None and region_id not in seen:
        seen.add(region_id)
        out.append(region_id)
        r = db.get(Region, region_id)
        region_id = r.parent_id if r else None
    return out


def by_code(db: Session, code: str) -> Region | None:
    return db.scalar(select(Region).where(Region.code == code))
