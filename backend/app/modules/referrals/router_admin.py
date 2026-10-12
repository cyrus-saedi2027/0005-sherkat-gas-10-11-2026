from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request
from pydantic import BaseModel, Field
from sqlalchemy import func, select

from app.core.deps import DB, StaffCtx, require
from app.core.pagination import Page, PageParams, page_params
from app.core.rbac import P
from app.modules.referrals import service
from app.modules.referrals.models import Referral
from app.modules.referrals.schemas import ReferralOut
from app.modules.users.models import User

router = APIRouter(prefix="/referrals", tags=["admin:referrals"])


class ReviewIn(BaseModel):
    approve: bool
    reason: str = Field(min_length=3, max_length=300)


def _out(db, r: Referral) -> ReferralOut:
    names = {u.id: " ".join(x for x in (u.first_name, u.last_name) if x) or f"کاربر {u.id}"
             for u in db.scalars(select(User).where(User.id.in_([r.referrer_user_id, r.referee_user_id]))).all()}
    return ReferralOut(id=r.id, referrer_user_id=r.referrer_user_id, referrer_name=names.get(r.referrer_user_id),
                       referee_user_id=r.referee_user_id, referee_name=names.get(r.referee_user_id), code_used=r.code_used,
                       status=r.status, reason=r.reason, signals=r.signals or {}, qualified_at=r.qualified_at,
                       created_at=r.created_at)


@router.get("", response_model=Page[ReferralOut])
def list_referrals(db: DB, p: PageParams = Depends(page_params),
                   status: Annotated[str | None, Query(pattern="^(pending|rewarded|capped|suspicious|rejected)$")] = None,
                   referrer_user_id: int | None = None, _s: StaffCtx = require(P.REFERRALS_VIEW)) -> Page[ReferralOut]:
    stmt = select(Referral).order_by(Referral.id.desc())
    if status:
        stmt = stmt.where(Referral.status == status)
    if referrer_user_id:
        stmt = stmt.where(Referral.referrer_user_id == referrer_user_id)
    total = int(db.scalar(select(func.count()).select_from(stmt.order_by(None).subquery())) or 0)
    rows = db.scalars(stmt.limit(p.size).offset(p.offset)).all()
    return Page(items=[_out(db, r) for r in rows], total=total, page=p.page, size=p.size)


@router.post("/{referral_id}/review", response_model=ReferralOut)
def review(referral_id: int, body: ReviewIn, request: Request, db: DB, staff: StaffCtx = require(P.REFERRALS_REVIEW)) -> ReferralOut:
    return _out(db, service.review(db, referral_id, body.approve, body.reason, staff.actor, request))
