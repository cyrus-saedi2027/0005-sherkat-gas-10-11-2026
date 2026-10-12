"""Dashboard KPIs (R27, R37). Each block is a provider so later stages add KPIs without touching this file's callers.

Providers receive a Filters object (region / date range / status / expert, R27) and
return (kpis, series, breakdown). They must stay cheap: aggregate SQL only.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta

from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session

from app.core import clock, jalali
from app.core import settings_registry as reg
from app.core.deps import StaffCtx
from app.core.rbac import P
from app.modules.dashboard.schemas import Kpi, Series, SeriesPoint
from app.modules.points.models import PointsLedger
from app.modules.readings.models import MeterReading
from app.modules.regions.service import descendants
from app.modules.subscribers.models import Subscriber
from app.modules.users.models import User


@dataclass
class Filters:
    region_ids: set[int] | None
    date_from: datetime
    date_to: datetime
    status: str | None
    expert_id: int | None


Provider = Callable[[Session, Filters, StaffCtx], tuple[list[Kpi], list[Series], dict[str, list[dict]]]]
PROVIDERS: list[tuple[P, Provider]] = []


def provider(perm: P) -> Callable[[Provider], Provider]:
    def deco(fn: Provider) -> Provider:
        PROVIDERS.append((perm, fn))
        return fn

    return deco


def make_filters(db: Session, region_id: int | None, date_from: date | None, date_to: date | None,
                 status: str | None, expert_id: int | None) -> Filters:
    today = jalali.to_tehran(clock.now()).date()
    df = date_from or today - timedelta(days=29)
    dt = date_to or today
    return Filters(descendants(db, region_id) if region_id else None,
                   datetime.combine(df, time(0), tzinfo=jalali.TEHRAN),
                   datetime.combine(dt + timedelta(days=1), time(0), tzinfo=jalali.TEHRAN), status, expert_id)


def _region(stmt: Select, f: Filters) -> Select:
    return stmt.where(Subscriber.region_id.in_(f.region_ids)) if f.region_ids else stmt


def eligible_condition(db: Session):
    t = reg.get_int(db, "eligibility.threshold_m3")
    basis = reg.get(db, "eligibility.threshold_basis")
    if basis == "monthly_avg":
        return Subscriber.baseline_annual_m3 / 12 >= t
    if basis == "period":  # dashboard approximation: average period share of the annual baseline
        return Subscriber.baseline_annual_m3 / 12 * int(reg.get(db, "reading.period_months")) >= t
    return Subscriber.baseline_annual_m3 >= t


def daily_series(db: Session, f: Filters, col, stmt: Select) -> list[SeriesPoint]:
    """Bucket timestamps into Tehran calendar days in Python (portable across SQLite/PostgreSQL)."""
    counts: dict[date, int] = {}
    for (ts,) in db.execute(stmt.with_only_columns(col).where(col >= f.date_from, col < f.date_to)).all():
        d = jalali.to_tehran(ts).date()
        counts[d] = counts.get(d, 0) + 1
    out, d = [], jalali.to_tehran(f.date_from).date()
    end = jalali.to_tehran(f.date_to).date()
    while d < end:
        out.append(SeriesPoint(label=jalali.format_date(d), value=counts.get(d, 0)))
        d += timedelta(days=1)
    return out


@provider(P.SUBSCRIBERS_VIEW)
def subscribers_block(db: Session, f: Filters, _s: StaffCtx):
    base = _region(select(func.count()).select_from(Subscriber).where(Subscriber.is_active.is_(True)), f)
    total = db.scalar(base) or 0
    eligible = db.scalar(base.where(eligible_condition(db))) or 0
    reg_stmt = _region(select(func.count()).select_from(User).join(Subscriber, Subscriber.id == User.subscriber_id), f)
    registered = db.scalar(reg_stmt) or 0
    new_regs = db.scalar(reg_stmt.where(User.created_at >= f.date_from, User.created_at < f.date_to)) or 0
    series_stmt = _region(select(User.created_at).join(Subscriber, Subscriber.id == User.subscriber_id), f)
    pct = round(registered / eligible * 100, 1) if eligible else 0
    return (
        [Kpi(key="subscribers_total", title="مشترکان فهرست مجاز", value=total, unit="مشترک"),
         Kpi(key="subscribers_eligible", title="مشترکان واجد شرایط", value=eligible, unit="مشترک", tone="info"),
         Kpi(key="users_registered", title="ثبت‌نام‌شده", value=registered, unit="کاربر", tone="ok",
             hint=f"{pct}٪ از واجدین شرایط"),
         Kpi(key="users_new", title="ثبت‌نام در بازه", value=new_regs, unit="کاربر")],
        [Series(key="registrations", title="ثبت‌نام روزانه", points=daily_series(db, f, User.created_at, series_stmt))],
        {},
    )


@provider(P.READINGS_VIEW)
def readings_block(db: Session, f: Filters, _s: StaffCtx):
    cur = _region(select(func.count()).select_from(MeterReading).join(Subscriber, Subscriber.id == MeterReading.subscriber_id)
                  .where(MeterReading.is_current.is_(True)), f)
    pending = db.scalar(cur.where(MeterReading.status == "pending")) or 0
    flagged = db.scalar(cur.where(MeterReading.status == "flagged")) or 0
    in_range = cur.where(MeterReading.created_at >= f.date_from, MeterReading.created_at < f.date_to)
    if f.expert_id:
        in_range = in_range.where(MeterReading.reviewer_id == f.expert_id)
    approved = db.scalar(in_range.where(MeterReading.status == "approved")) or 0
    by_status = dict(db.execute(in_range.with_only_columns(MeterReading.status, func.count()).group_by(MeterReading.status)).all())
    saved = db.scalar(_region(select(func.coalesce(func.sum(MeterReading.baseline_m3 - MeterReading.consumption_m3), 0))
                              .join(Subscriber, Subscriber.id == MeterReading.subscriber_id)
                              .where(MeterReading.status == "approved", MeterReading.is_current.is_(True),
                                     MeterReading.consumption_m3.is_not(None), MeterReading.baseline_m3.is_not(None),
                                     MeterReading.consumption_m3 < MeterReading.baseline_m3,
                                     MeterReading.reviewed_at >= f.date_from, MeterReading.reviewed_at < f.date_to), f)) or 0
    s_stmt = _region(select(MeterReading.created_at).join(Subscriber, Subscriber.id == MeterReading.subscriber_id), f)
    return (
        [Kpi(key="readings_pending", title="قرائت‌های در انتظار بررسی", value=pending, unit="قرائت", tone="warn"),
         Kpi(key="readings_flagged", title="نیازمند بررسی کارشناسی", value=flagged, unit="قرائت", tone="crit"),
         Kpi(key="readings_approved", title="قرائت تأییدشده در بازه", value=approved, unit="قرائت", tone="ok"),
         Kpi(key="gas_saved_m3", title="گاز صرفه‌جویی‌شده", value=round(float(saved), 1), unit="مترمکعب", tone="ok")],
        [Series(key="readings", title="قرائت‌های ثبت‌شده", points=daily_series(db, f, MeterReading.created_at, s_stmt))],
        {"readings_by_status": [{"key": k, "value": int(v)} for k, v in by_status.items()]},
    )


@provider(P.POINTS_VIEW)
def points_block(db: Session, f: Filters, _s: StaffCtx):
    q = select(func.coalesce(func.sum(PointsLedger.amount), 0)).where(PointsLedger.amount > 0,
                                                                       PointsLedger.status != "reversed",
                                                                       PointsLedger.created_at >= f.date_from,
                                                                       PointsLedger.created_at < f.date_to)
    if f.region_ids:
        q = q.join(User, User.id == PointsLedger.user_id).join(Subscriber, Subscriber.id == User.subscriber_id) \
             .where(Subscriber.region_id.in_(f.region_ids))
    issued = int(db.scalar(q) or 0)
    rate = reg.get_int(db, "finance.point_rial_rate")
    suspended = int(db.scalar(select(func.coalesce(func.sum(PointsLedger.amount), 0)).where(PointsLedger.status == "suspended")) or 0)
    return (
        [Kpi(key="points_issued", title="امتیاز صادرشده در بازه", value=issued, unit="امتیاز", tone="accent"),
         Kpi(key="points_issued_rial", title="ارزش ریالی امتیازها", value=issued * rate, unit="ریال", tone="accent"),
         Kpi(key="points_suspended", title="امتیاز معلق", value=suspended, unit="امتیاز", tone="crit")],
        [], {},
    )


def build(db: Session, staff: StaffCtx, f: Filters):
    kpis: list[Kpi] = []
    series: list[Series] = []
    breakdown: dict[str, list[dict]] = {}
    for perm, fn in PROVIDERS:
        if perm in staff.perms:
            k, s, b = fn(db, f, staff)
            kpis += k
            series += s
            breakdown.update(b)
    return kpis, series, breakdown


@provider(P.CASES_VIEW_ALL)
def cases_block(db: Session, f: Filters, _s: StaffCtx):
    from app.modules.cases.models import Case, CaseEstimate
    from app.modules.cases.service import OPEN_STATUSES

    q = select(func.count()).select_from(Case)
    if f.region_ids:
        q = q.where(Case.region_id.in_(f.region_ids))
    if f.expert_id:
        q = q.where(Case.ambassador_id == f.expert_id)
    referred = db.scalar(q.where(Case.created_at >= f.date_from, Case.created_at < f.date_to)) or 0
    open_n = db.scalar(q.where(Case.status.in_(OPEN_STATUSES))) or 0
    unassigned = db.scalar(q.where(Case.status == "new", Case.ambassador_id.is_(None))) or 0
    by_tier = dict(db.execute(q.with_only_columns(Case.tier, func.count()).where(Case.tier.is_not(None)).group_by(Case.tier)).all())
    by_status = dict(db.execute(q.with_only_columns(Case.status, func.count()).group_by(Case.status)).all())
    cost_q = select(func.coalesce(func.sum(CaseEstimate.program_share_rial), 0)).join(Case, Case.id == CaseEstimate.case_id) \
        .where(CaseEstimate.status == "accepted", CaseEstimate.created_at >= f.date_from, CaseEstimate.created_at < f.date_to)
    if f.region_ids:
        cost_q = cost_q.where(Case.region_id.in_(f.region_ids))
    cost = int(db.scalar(cost_q) or 0)
    series_stmt = select(Case.created_at)
    if f.region_ids:
        series_stmt = series_stmt.where(Case.region_id.in_(f.region_ids))
    return (
        [Kpi(key="cases_referred", title="پرونده‌های ارجاع‌شده در بازه", value=referred, unit="پرونده", tone="info"),
         Kpi(key="cases_open", title="پرونده‌های باز", value=open_n, unit="پرونده"),
         Kpi(key="cases_unassigned", title="پرونده‌های بدون سفیر", value=unassigned, unit="پرونده", tone="warn"),
         Kpi(key="service_cost_rial", title="هزینهٔ خدمات (سهم طرح)", value=cost, unit="ریال", tone="accent")],
        [Series(key="cases", title="پرونده‌های جدید", points=daily_series(db, f, Case.created_at, series_stmt))],
        {"cases_by_tier": [{"key": k, "value": int(v)} for k, v in by_tier.items()],
         "cases_by_status": [{"key": k, "value": int(v)} for k, v in by_status.items()]},
    )


@provider(P.CASES_VIEW_OWN)
def my_cases_block(db: Session, f: Filters, s: StaffCtx):
    from app.modules.cases.models import Case, CaseVisit
    from app.modules.cases.service import OPEN_STATUSES

    if s.can(P.CASES_VIEW_ALL):
        return [], [], {}
    open_n = db.scalar(select(func.count()).where(Case.ambassador_id == s.id, Case.status.in_(OPEN_STATUSES))) or 0
    now = clock.now()
    week = db.scalar(select(func.count()).where(CaseVisit.ambassador_id == s.id, CaseVisit.status == "scheduled",
                                                CaseVisit.scheduled_start >= now,
                                                CaseVisit.scheduled_start < now + timedelta(days=7))) or 0
    to_call = db.scalar(select(func.count()).where(Case.ambassador_id == s.id, Case.status == "assigned")) or 0
    done = db.scalar(select(func.count()).where(Case.ambassador_id == s.id, Case.status == "completed",
                                                Case.completed_at >= f.date_from, Case.completed_at < f.date_to)) or 0
    return ([Kpi(key="my_open_cases", title="پرونده‌های باز من", value=open_n, unit="پرونده", tone="info"),
             Kpi(key="my_to_call", title="منتظر تماس اول", value=to_call, unit="پرونده", tone="warn"),
             Kpi(key="my_visits_week", title="بازدیدهای ۷ روز آینده", value=week, unit="بازدید"),
             Kpi(key="my_completed", title="تکمیل‌شده در بازه", value=done, unit="پرونده", tone="ok")], [], {})


@provider(P.REFERRALS_VIEW)
def referrals_block(db: Session, f: Filters, _s: StaffCtx):
    from app.modules.referrals.models import Referral

    rows = dict(db.execute(select(Referral.status, func.count()).where(Referral.created_at >= f.date_from,
                                                                       Referral.created_at < f.date_to)
                           .group_by(Referral.status)).all())
    total = sum(int(v) for v in rows.values())
    rewarded = int(rows.get("rewarded", 0))
    return ([Kpi(key="referrals_valid", title="معرفی‌های معتبر", value=rewarded, unit="معرفی", tone="ok",
                 hint=f"نرخ تبدیل {round(rewarded / total * 100) if total else 0}٪"),
             Kpi(key="referrals_suspicious", title="معرفی‌های مشکوک", value=int(rows.get("suspicious", 0)), unit="معرفی", tone="crit")],
            [], {"referrals_by_status": [{"key": k, "value": int(v)} for k, v in rows.items()]})
