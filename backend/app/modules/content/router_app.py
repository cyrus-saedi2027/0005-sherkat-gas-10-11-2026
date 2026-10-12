from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Query
from sqlalchemy import select

from app.core.deps import DB, CurrentUser
from app.core.errors import AppError
from app.modules.content import service
from app.modules.content.models import Article
from app.modules.content.schemas import ArticleDetail, ArticleOut
from app.modules.users.models import User

router = APIRouter(prefix="/content", tags=["app:content"])


@router.get("", response_model=list[ArticleOut])
def feed(user: CurrentUser, db: DB, category: Annotated[str | None, Query(pattern="^(tip|article|news|guide)$")] = None,
         limit: Annotated[int, Query(ge=1, le=100)] = 50) -> list[ArticleOut]:
    u = db.get(User, user.id)
    items = service.visible_to(db, u.tier if u else None)
    if category:
        items = [a for a in items if a.category == category]
    return [service.out(a) for a in items[:limit]]


@router.get("/{slug}", response_model=ArticleDetail)
def read(slug: str, user: CurrentUser, db: DB) -> ArticleDetail:
    u = db.get(User, user.id)
    a = db.scalar(select(Article).where(Article.slug == slug))
    if a is None or a not in service.visible_to(db, u.tier if u else None):
        raise AppError("not_found", "مطلب پیدا نشد.", 404)
    return service.detail(a)
