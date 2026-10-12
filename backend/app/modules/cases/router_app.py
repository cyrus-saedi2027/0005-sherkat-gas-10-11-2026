from __future__ import annotations

from fastapi import APIRouter, Request
from sqlalchemy import select

from app.core.deps import DB, CurrentUser
from app.modules.cases import presenter, service
from app.modules.cases.models import Case
from app.modules.cases.schemas import ConsentIn, UserCaseOut

router = APIRouter(prefix="/case", tags=["app:case"])


@router.get("", response_model=UserCaseOut | None)
def my_case(user: CurrentUser, db: DB) -> UserCaseOut | None:
    c = db.scalar(select(Case).where(Case.user_id == user.id).order_by(Case.id.desc()))
    return presenter.user_case(db, c) if c else None


@router.post("/consent", response_model=UserCaseOut)
def consent(body: ConsentIn, user: CurrentUser, request: Request, db: DB) -> UserCaseOut:
    """R19: execution in the high-cost group (or any subscriber share) needs the subscriber's approval."""
    c = service.open_case_for(db, user.id)
    if c is None:
        from app.core.errors import AppError

        raise AppError("not_found", "پروندهٔ فعالی ندارید.", 404)
    return presenter.user_case(db, service.respond_estimate(db, c, user.id, body.accept, request))
