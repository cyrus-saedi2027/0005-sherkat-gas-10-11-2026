from __future__ import annotations

from collections import Counter
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core import clock
from app.core.errors import AppError
from app.modules.points import service as points
from app.modules.surveys.models import Survey, SurveyQuestion, SurveyResponse
from app.modules.surveys.schemas import QuestionOut, QuestionResult, SurveyIn, SurveyOut, SurveyResults


def questions(db: Session, sid: int) -> list[SurveyQuestion]:
    return list(db.scalars(select(SurveyQuestion).where(SurveyQuestion.survey_id == sid).order_by(SurveyQuestion.sort)).all())


def out(db: Session, s: Survey, user_id: int | None = None) -> SurveyOut:
    n = db.scalar(select(func.count()).where(SurveyResponse.survey_id == s.id)) or 0
    answered = bool(user_id and db.scalar(select(SurveyResponse.id).where(SurveyResponse.survey_id == s.id,
                                                                          SurveyResponse.user_id == user_id)))
    r = points.rule(db, "survey_completed")
    return SurveyOut(id=s.id, title=s.title, description=s.description, status=s.status, starts_at=s.starts_at, ends_at=s.ends_at,
                     target_tiers=list(s.target_tiers or []),
                     questions=[QuestionOut(id=q.id, kind=q.kind, text=q.text, options=list(q.options or []), required=q.required)
                                for q in questions(db, s.id)],
                     responses=int(n), answered=answered, points=r.points if r and r.is_active else 0, created_at=s.created_at)


def save(db: Session, s: Survey | None, body: SurveyIn, staff_id: int) -> Survey:
    for q in body.questions:
        if q.kind in ("single", "multi") and len([o for o in q.options if o.strip()]) < 2:
            raise AppError("validation_error", f"سؤال «{q.text}» دست‌کم دو گزینه لازم دارد.", 422)
    if s is None:
        s = Survey(created_by=staff_id)
        db.add(s)
    elif s.status != "draft" and db.scalar(select(SurveyResponse.id).where(SurveyResponse.survey_id == s.id)):
        raise AppError("bad_state", "نظرسنجی پاسخ دریافت کرده و قابل ویرایش نیست.", 409)
    s.title, s.description, s.starts_at, s.ends_at, s.target_tiers = (body.title, body.description, body.starts_at, body.ends_at,
                                                                       list(body.target_tiers))
    db.flush()
    for q in questions(db, s.id):
        db.delete(q)
    for i, q in enumerate(body.questions):
        db.add(SurveyQuestion(survey_id=s.id, kind=q.kind, text=q.text, options=[o.strip() for o in q.options if o.strip()],
                              required=q.required, sort=i))
    db.flush()
    return s


def available(db: Session, tier: str | None) -> list[Survey]:
    now = clock.now()
    rows = db.scalars(select(Survey).where(Survey.status == "active").order_by(Survey.id.desc())).all()
    return [s for s in rows if (not s.starts_at or s.starts_at <= now) and (not s.ends_at or s.ends_at > now)
            and (not s.target_tiers or (tier and tier in s.target_tiers))]


def answer(db: Session, s: Survey, user_id: int, tier: str | None, answers: dict[str, Any]) -> SurveyResponse:
    if s not in available(db, tier):
        raise AppError("not_found", "این نظرسنجی در دسترس نیست.", 404)
    if db.scalar(select(SurveyResponse.id).where(SurveyResponse.survey_id == s.id, SurveyResponse.user_id == user_id)):
        raise AppError("already_answered", "قبلاً به این نظرسنجی پاسخ داده‌اید.", 409)
    clean: dict[str, Any] = {}
    errors: dict[str, str] = {}
    for q in questions(db, s.id):
        v = answers.get(str(q.id))
        if v in (None, "", []):
            if q.required:
                errors[str(q.id)] = "پاسخ به این سؤال الزامی است."
            continue
        if q.kind == "single" and v not in q.options:
            errors[str(q.id)] = "گزینهٔ انتخاب‌شده معتبر نیست."
        elif q.kind == "multi" and (not isinstance(v, list) or any(x not in q.options for x in v)):
            errors[str(q.id)] = "گزینه‌های انتخاب‌شده معتبر نیست."
        elif q.kind == "rating" and (not isinstance(v, int) or not 1 <= v <= 5):
            errors[str(q.id)] = "امتیاز باید بین ۱ تا ۵ باشد."
        elif q.kind == "text" and (not isinstance(v, str) or len(v) > 2000):
            errors[str(q.id)] = "پاسخ متنی معتبر نیست."
        else:
            clean[str(q.id)] = v.strip() if isinstance(v, str) else v
    if errors:
        raise AppError("validation_error", "برخی پاسخ‌ها کامل یا معتبر نیست.", 422, {"fields": errors})
    r = SurveyResponse(survey_id=s.id, user_id=user_id, answers=clean)
    db.add(r)
    db.flush()
    points.award(db, user_id=user_id, event_type="survey_completed", idempotency_key=f"survey:{s.id}:{user_id}",
                 ref_type="survey", ref_id=s.id)  # R23: 10 points per survey (editable)
    return r


def results(db: Session, s: Survey) -> SurveyResults:
    resps = db.scalars(select(SurveyResponse).where(SurveyResponse.survey_id == s.id)).all()
    qs = []
    for q in questions(db, s.id):
        vals = [r.answers.get(str(q.id)) for r in resps if r.answers.get(str(q.id)) is not None]
        counts: Counter[str] = Counter()
        texts: list[str] = []
        avg = None
        if q.kind == "single":
            counts.update(str(v) for v in vals)
        elif q.kind == "multi":
            for v in vals:
                counts.update(str(x) for x in v)
        elif q.kind == "rating":
            counts.update(str(v) for v in vals)
            avg = round(sum(vals) / len(vals), 2) if vals else None
        else:
            texts = [str(v) for v in vals][-200:]
        qs.append(QuestionResult(id=q.id, text=q.text, kind=q.kind, counts=dict(counts), average=avg, texts=texts))
    return SurveyResults(survey=out(db, s), responses=len(resps), questions=qs)
