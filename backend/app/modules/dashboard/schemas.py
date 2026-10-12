from __future__ import annotations

from pydantic import BaseModel


class Kpi(BaseModel):
    key: str
    title: str
    value: float
    unit: str = ""
    tone: str = "neutral"
    hint: str | None = None


class SeriesPoint(BaseModel):
    label: str  # Jalali date "1405/07/20" or period "1405-07"
    value: float


class Series(BaseModel):
    key: str
    title: str
    points: list[SeriesPoint]


class DashboardOut(BaseModel):
    role_view: str
    kpis: list[Kpi]
    series: list[Series]
    breakdown: dict[str, list[dict[str, float | str]]]
