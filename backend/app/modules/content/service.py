from __future__ import annotations

import re
import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core import clock
from app.core.errors import AppError
from app.modules.content.models import Article
from app.modules.content.schemas import ArticleDetail, ArticleIn, ArticleOut
from app.modules.files import service as files


def reading_minutes(body: str) -> int:
    words = len(re.findall(r"\S+", body))
    return max(1, round(words / 180))  # Persian reading speed is slower than English


def out(a: Article) -> ArticleOut:
    return ArticleOut(id=a.id, slug=a.slug, title=a.title, summary=a.summary, category=a.category,
                      target_tiers=list(a.target_tiers or []), status=a.status, published_at=a.published_at,
                      cover_url=files.url(a.cover_file_id), reading_minutes=a.reading_minutes, updated_at=a.updated_at)


def detail(a: Article) -> ArticleDetail:
    return ArticleDetail(**out(a).model_dump(), body=a.body, cover_file_id=a.cover_file_id)


def upsert(db: Session, a: Article | None, body: ArticleIn, author_id: int) -> Article:
    slug = body.slug or (a.slug if a else f"a-{uuid.uuid4().hex[:10]}")
    if db.scalar(select(Article.id).where(Article.slug == slug, Article.id != (a.id if a else -1))):
        raise AppError("slug_taken", "این نشانی (slug) تکراری است.", 409)
    if body.cover_file_id and files.get(db, body.cover_file_id) is None:
        raise AppError("not_found", "تصویر کاور پیدا نشد.", 404)
    if a is None:
        a = Article(author_id=author_id)
        db.add(a)
    a.slug, a.title, a.summary, a.body = slug, body.title.strip(), body.summary.strip(), body.body
    a.category, a.target_tiers, a.cover_file_id = body.category, sorted(set(body.target_tiers)), body.cover_file_id
    a.reading_minutes = reading_minutes(body.body)
    db.flush()
    return a


def set_status(a: Article, status: str) -> None:
    a.status = status
    if status == "published" and a.published_at is None:
        a.published_at = clock.now()


def visible_to(db: Session, tier: str | None):
    """Published articles targeted at everyone or at the user's tier (R17–R19)."""
    stmt = select(Article).where(Article.status == "published")
    articles = db.scalars(stmt.order_by(Article.published_at.desc())).all()
    return [a for a in articles if not a.target_tiers or (tier and tier in a.target_tiers)]


