from __future__ import annotations

from fastapi import APIRouter, Request
from sqlalchemy import select

from app.core import audit
from app.core.deps import DB, StaffCtx, require
from app.core.errors import AppError
from app.core.rbac import P
from app.modules.surveys import service
from app.modules.surveys.models import Survey
from app.modules.surveys.schemas import StatusIn, SurveyIn, SurveyOut, SurveyResults

router = APIRouter(prefix="/surveys", tags=["admin:surveys"])


def _load(db, sid: int) -> Survey:
    s = db.get(Survey, sid)
    if s is None:
        raise AppError("not_found", "نظرسنجی پیدا نشد.", 404)
    return s


@router.get("", response_model=list[SurveyOut])
def list_surveys(db: DB, _s: StaffCtx = require(P.SURVEYS_VIEW)) -> list[SurveyOut]:
    return [service.out(db, s) for s in db.scalars(select(Survey).order_by(Survey.id.desc()).limit(200)).all()]


@router.post("", response_model=SurveyOut, status_code=201)
def create(body: SurveyIn, request: Request, db: DB, staff: StaffCtx = require(P.SURVEYS_MANAGE)) -> SurveyOut:
    s = service.save(db, None, body, staff.id)
    audit.record(db, staff.actor, "survey.create", "survey", s.id, None, {"title": s.title}, request)
    return service.out(db, s)


@router.put("/{survey_id}", response_model=SurveyOut)
def update(survey_id: int, body: SurveyIn, request: Request, db: DB, staff: StaffCtx = require(P.SURVEYS_MANAGE)) -> SurveyOut:
    s = service.save(db, _load(db, survey_id), body, staff.id)
    audit.record(db, staff.actor, "survey.update", "survey", s.id, None, {"title": s.title}, request)
    return service.out(db, s)


@router.post("/{survey_id}/status", response_model=SurveyOut)
def set_status(survey_id: int, body: StatusIn, request: Request, db: DB, staff: StaffCtx = require(P.SURVEYS_MANAGE)) -> SurveyOut:
    s = _load(db, survey_id)
    before = s.status
    s.status = body.status
    audit.record(db, staff.actor, "survey.status", "survey", s.id, {"status": before}, {"status": s.status}, request)
    return service.out(db, s)


@router.get("/{survey_id}/results", response_model=SurveyResults)
def results(survey_id: int, db: DB, _s: StaffCtx = require(P.SURVEYS_VIEW)) -> SurveyResults:
    return service.results(db, _load(db, survey_id))
