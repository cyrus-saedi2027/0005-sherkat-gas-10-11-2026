from __future__ import annotations

from pydantic import BaseModel


class PeriodPoint(BaseModel):
    period_key: str
    label: str
    consumption_m3: float | None
    baseline_m3: float | None
    reduction_pct: float | None
    status: str | None


class MonthBaseline(BaseModel):
    jmonth: int
    label: str
    baseline_m3: float | None
    years: dict[int, float]


class Totals(BaseModel):
    saved_m3: float
    avg_reduction_pct: float | None
    approved_readings: int
    best_period: str | None
    co2_saved_kg: float
    target_reduction_pct: int


class ConsumptionOut(BaseModel):
    baseline_annual_m3: float | None
    baseline_years: list[int]
    periods: list[PeriodPoint]
    monthly_baseline: list[MonthBaseline]
    totals: Totals
