"""Consumption analysis for the subscriber (R04, R45): actual vs. the same period's 3-year average."""

from __future__ import annotations

from fastapi import APIRouter
from sqlalchemy import select

from app.core import clock, jalali
from app.core import settings_registry as reg
from app.core.deps import DB, CurrentUser
from app.modules.analytics.schemas import ConsumptionOut, MonthBaseline, PeriodPoint, Totals
from app.modules.readings.models import MeterReading
from app.modules.subscribers import service as subscribers
from app.modules.subscribers.models import Subscriber

router = APIRouter(prefix="/analytics", tags=["app:analytics"])
CO2_KG_PER_M3 = 1.9  # combustion factor for natural gas, used only as an illustrative equivalent


@router.get("/consumption", response_model=ConsumptionOut)
def consumption(user: CurrentUser, db: DB) -> ConsumptionOut:
    months = int(reg.get(db, "reading.period_months"))
    sub = db.get(Subscriber, user.subscriber_id)
    current = jalali.period_key(clock.now(), months)
    keys = [jalali.shift_period(current, -months * i) for i in range(11, -1, -1)]
    readings = {r.period_key: r for r in db.scalars(select(MeterReading).where(
        MeterReading.subscriber_id == user.subscriber_id, MeterReading.is_current.is_(True),
        MeterReading.period_key.in_(keys))).all()}
    periods = []
    for k in keys:
        r = readings.get(k)
        approved = r is not None and r.status == "approved"
        periods.append(PeriodPoint(period_key=k, label=jalali.period_label(k),
                                   consumption_m3=r.consumption_m3 if approved else None,
                                   baseline_m3=r.baseline_m3 if approved and r.baseline_m3 is not None
                                   else subscribers.period_baseline(db, user.subscriber_id, k, months),
                                   reduction_pct=r.reduction_pct if approved else None, status=r.status if r else None))
    hist = subscribers.history_series(db, user.subscriber_id)
    monthly = [MonthBaseline(jmonth=m, label=jalali.MONTHS_FA[m - 1], baseline_m3=subscribers.monthly_baseline(db, user.subscriber_id, m),
                             years={y: v[m] for y, v in sorted(hist.items()) if m in v}) for m in range(1, 13)]
    done = [p for p in periods if p.consumption_m3 is not None and p.baseline_m3]
    saved = sum(max(0.0, (p.baseline_m3 or 0) - (p.consumption_m3 or 0)) for p in done)
    reds = [p.reduction_pct for p in done if p.reduction_pct is not None]
    best = max(done, key=lambda p: p.reduction_pct or -1e9).period_key if done else None
    years = list(range(jalali.jdate_of(clock.now()).year - reg.get_int(db, "eligibility.baseline_years"),
                       jalali.jdate_of(clock.now()).year))
    return ConsumptionOut(baseline_annual_m3=sub.baseline_annual_m3 if sub else None, baseline_years=years, periods=periods,
                          monthly_baseline=monthly,
                          totals=Totals(saved_m3=round(saved, 1), avg_reduction_pct=round(sum(reds) / len(reds), 1) if reds else None,
                                        approved_readings=len(done), best_period=best,
                                        co2_saved_kg=round(saved * CO2_KG_PER_M3, 1),
                                        target_reduction_pct=reg.get_int(db, "points.reduction_required_pct")))
