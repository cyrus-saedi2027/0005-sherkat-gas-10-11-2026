"""Authorised-list lookups and consumption baselines (R04, R07, R09, R14)."""

from __future__ import annotations

from collections import defaultdict

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core import clock, crypto, jalali
from app.core import settings_registry as reg
from app.modules.subscribers.models import ConsumptionHistory, Subscriber


def mobile_bidx(mobile: str) -> str:
    return crypto.blind_index(mobile, purpose="mobile") or ""


def find_match(db: Session, subscription_no: str, mobile: str) -> Subscriber | None:
    """Match on the COMBINATION of subscription number and mobile (R07)."""
    return db.scalar(select(Subscriber).where(Subscriber.subscription_no == subscription_no,
                                              Subscriber.mobile_bidx == mobile_bidx(mobile)))


def _baseline_years(db: Session, ref_year: int | None = None) -> list[int]:
    n = reg.get_int(db, "eligibility.baseline_years")
    y = ref_year if ref_year is not None else jalali.jdate_of(clock.now()).year
    return list(range(y - n, y))


def monthly_baseline(db: Session, subscriber_id: int, jmonth: int, ref_year: int | None = None) -> float | None:
    """Mean consumption of the same month over the baseline years (R04)."""
    years = _baseline_years(db, ref_year)
    v = db.scalar(select(func.avg(ConsumptionHistory.volume_m3)).where(
        ConsumptionHistory.subscriber_id == subscriber_id, ConsumptionHistory.jmonth == jmonth,
        ConsumptionHistory.jyear.in_(years)))
    return float(v) if v is not None else None


def period_baseline(db: Session, subscriber_id: int, period_key: str, months: int = 1) -> float | None:
    y, m = jalali.parse_period(period_key)
    total, seen = 0.0, False
    for i in range(months):
        mm = (m - 1 + i) % 12 + 1
        b = monthly_baseline(db, subscriber_id, mm, ref_year=y if mm >= m else y + 1)
        if b is not None:
            total += b
            seen = True
    return total if seen else None


def annual_baseline(db: Session, subscriber_id: int, ref_year: int | None = None) -> float | None:
    years = _baseline_years(db, ref_year)
    rows = db.execute(select(ConsumptionHistory.jyear, func.sum(ConsumptionHistory.volume_m3))
                      .where(ConsumptionHistory.subscriber_id == subscriber_id, ConsumptionHistory.jyear.in_(years))
                      .group_by(ConsumptionHistory.jyear)).all()
    if not rows:
        return None
    return float(sum(v for _, v in rows) / len(rows))


def refresh_baselines(db: Session, subscriber_ids: list[int] | None = None) -> int:
    stmt = select(Subscriber)
    if subscriber_ids is not None:
        stmt = stmt.where(Subscriber.id.in_(subscriber_ids))
    n = 0
    for s in db.scalars(stmt).all():
        s.baseline_annual_m3 = annual_baseline(db, s.id)
        n += 1
    db.flush()
    return n


def eligibility_value(db: Session, s: Subscriber) -> float | None:
    basis = reg.get(db, "eligibility.threshold_basis")
    annual = s.baseline_annual_m3 if s.baseline_annual_m3 is not None else annual_baseline(db, s.id)
    if basis == "annual":
        return annual
    if basis == "monthly_avg":
        return annual / 12 if annual is not None else None
    months = int(reg.get(db, "reading.period_months"))
    return period_baseline(db, s.id, jalali.period_key(clock.now(), months), months)


def is_eligible(db: Session, s: Subscriber | None) -> bool:
    """R09: in the list, active, and consumption ≥ threshold. Missing history = not eligible."""
    if s is None or not s.is_active:
        return False
    v = eligibility_value(db, s)
    return v is not None and v >= reg.get_int(db, "eligibility.threshold_m3")


def history_series(db: Session, subscriber_id: int) -> dict[int, dict[int, float]]:
    out: dict[int, dict[int, float]] = defaultdict(dict)
    for r in db.scalars(select(ConsumptionHistory).where(ConsumptionHistory.subscriber_id == subscriber_id)
                        .order_by(ConsumptionHistory.jyear, ConsumptionHistory.jmonth)).all():
        out[r.jyear][r.jmonth] = r.volume_m3
    return dict(out)
