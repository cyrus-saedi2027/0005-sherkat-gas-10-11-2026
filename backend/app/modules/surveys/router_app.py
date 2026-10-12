from __future__ import annotations

from fastapi import APIRouter

from app.core.deps import DB, CurrentUser
from app.core.errors import AppError
from app.modules.surveys import service
from app.modules.surveys.models import Survey
from app.modules.surveys.schemas import AnswerIn, SurveyOut
from app.modules.users.models import User

router = APIRouter(prefix="/surveys", tags=["app:surveys"])


@router.get("", response_model=list[SurveyOut])
def available(user: CurrentUser, db: DB) -> list[SurveyOut]:
    u = db.get(User, user.id)
    return [service.out(db, s, user.id) for s in service.available(db, u.tier if u else None)]


@router.post("/{survey_id}/answers", response_model=SurveyOut, status_code=201)
def answer(survey_id: int, body: AnswerIn, user: CurrentUser, db: DB) -> SurveyOut:
    s = db.get(Survey, survey_id)
    if s is None:
        raise AppError("not_found", "نظرسنجی پیدا نشد.", 404)
    u = db.get(User, user.id)
    service.answer(db, s, user.id, u.tier if u else None, body.answers)
    return service.out(db, s, user.id)
