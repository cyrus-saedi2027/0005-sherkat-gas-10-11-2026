from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, File, Query, Request, UploadFile
from sqlalchemy import func, select

from app.core import audit
from app.core.deps import DB, StaffCtx, require
from app.core.errors import AppError
from app.core.pagination import Page, PageParams, page_params
from app.core.rbac import P
from app.modules.content import service
from app.modules.content.models import Article
from app.modules.content.schemas import ArticleDetail, ArticleIn, ArticleOut, ArticleStatusIn
from app.modules.files import service as files

router = APIRouter(prefix="/content", tags=["admin:content"])


@router.get("", response_model=Page[ArticleOut])
def list_articles(db: DB, p: PageParams = Depends(page_params),
                  status: Annotated[str | None, Query(pattern="^(draft|published|archived)$")] = None,
                  q: Annotated[str | None, Query(max_length=60)] = None, _s: StaffCtx = require(P.CONTENT_VIEW)) -> Page[ArticleOut]:
    stmt = select(Article).order_by(Article.updated_at.desc())
    if status:
        stmt = stmt.where(Article.status == status)
    if q:
        stmt = stmt.where(Article.title.ilike(f"%{q}%"))
    total = int(db.scalar(select(func.count()).select_from(stmt.order_by(None).subquery())) or 0)
    return Page(items=[service.out(a) for a in db.scalars(stmt.limit(p.size).offset(p.offset)).all()], total=total,
                page=p.page, size=p.size)


@router.post("/cover", status_code=201)
async def upload_cover(db: DB, file: Annotated[UploadFile, File()], staff: StaffCtx = require(P.CONTENT_MANAGE)) -> dict[str, str | None]:
    f = files.save_image(db, await file.read(20 * 1024 * 1024 + 1), purpose="content_cover", owner_type="staff",
                         owner_id=staff.id, original_name=file.filename)
    return {"file_id": f.id, "url": files.url(f.id)}


@router.post("", response_model=ArticleDetail, status_code=201)
def create(body: ArticleIn, request: Request, db: DB, staff: StaffCtx = require(P.CONTENT_MANAGE)) -> ArticleDetail:
    a = service.upsert(db, None, body, staff.id)
    audit.record(db, staff.actor, "content.create", "article", a.id, None, {"title": a.title}, request)
    return service.detail(a)


@router.get("/{article_id}", response_model=ArticleDetail)
def get_one(article_id: int, db: DB, _s: StaffCtx = require(P.CONTENT_VIEW)) -> ArticleDetail:
    a = db.get(Article, article_id)
    if a is None:
        raise AppError("not_found", "مطلب پیدا نشد.", 404)
    return service.detail(a)


@router.put("/{article_id}", response_model=ArticleDetail)
def update(article_id: int, body: ArticleIn, request: Request, db: DB, staff: StaffCtx = require(P.CONTENT_MANAGE)) -> ArticleDetail:
    a = db.get(Article, article_id)
    if a is None:
        raise AppError("not_found", "مطلب پیدا نشد.", 404)
    service.upsert(db, a, body, staff.id)
    audit.record(db, staff.actor, "content.update", "article", a.id, None, {"title": a.title}, request)
    return service.detail(a)


@router.post("/{article_id}/status", response_model=ArticleDetail)
def set_status(article_id: int, body: ArticleStatusIn, request: Request, db: DB,
               staff: StaffCtx = require(P.CONTENT_MANAGE)) -> ArticleDetail:
    a = db.get(Article, article_id)
    if a is None:
        raise AppError("not_found", "مطلب پیدا نشد.", 404)
    before = a.status
    service.set_status(a, body.status)
    audit.record(db, staff.actor, "content.status", "article", a.id, {"status": before}, {"status": a.status}, request)
    return service.detail(a)
