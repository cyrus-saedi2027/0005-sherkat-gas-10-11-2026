"""Jalali (Solar Hijri) helpers, always evaluated in Asia/Tehran.

Period keys look like "1405-07". A "month end" is the first instant of the
next Jalali month in Tehran — the moment pending points become available.
"""

from __future__ import annotations

from datetime import UTC, date, datetime, time
from zoneinfo import ZoneInfo

import jdatetime

TEHRAN = ZoneInfo("Asia/Tehran")

MONTHS_FA = (
    "فروردین", "اردیبهشت", "خرداد", "تیر", "مرداد", "شهریور",
    "مهر", "آبان", "آذر", "دی", "بهمن", "اسفند",
)


def to_tehran(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    return dt.astimezone(TEHRAN)


def jdate_of(dt_or_date: datetime | date) -> jdatetime.date:
    d = to_tehran(dt_or_date).date() if isinstance(dt_or_date, datetime) else dt_or_date
    return jdatetime.date.fromgregorian(date=d)


def period_key(dt_or_date: datetime | date, months_per_period: int = 1) -> str:
    """'YYYY-MM' of the period containing the instant/date (Tehran calendar).

    With 2-month periods the key is the first month of the pair (01,03,05…),
    so keys stay comparable as strings.
    """
    j = jdate_of(dt_or_date)
    m = j.month
    if months_per_period > 1:
        m = ((m - 1) // months_per_period) * months_per_period + 1
    return f"{j.year:04d}-{m:02d}"


def parse_period(key: str) -> tuple[int, int]:
    y, m = key.split("-")
    yi, mi = int(y), int(m)
    if not (1 <= mi <= 12) or yi < 1300:
        raise ValueError(f"bad period key {key!r}")
    return yi, mi


def shift_period(key: str, months: int) -> str:
    y, m = parse_period(key)
    idx = y * 12 + (m - 1) + months
    return f"{idx // 12:04d}-{idx % 12 + 1:02d}"


def month_start_utc(jy: int, jm: int) -> datetime:
    g = jdatetime.date(jy, jm, 1).togregorian()
    return datetime.combine(g, time(0, 0), tzinfo=TEHRAN).astimezone(UTC)


def period_bounds_utc(key: str, months_per_period: int = 1) -> tuple[datetime, datetime]:
    """[start, end) of the period in UTC."""
    y, m = parse_period(key)
    end_key = shift_period(key, months_per_period)
    ey, em = parse_period(end_key)
    return month_start_utc(y, m), month_start_utc(ey, em)


def next_month_start_utc(dt: datetime) -> datetime:
    """First instant of the Jalali month after `dt` (Tehran) — points release moment (R20)."""
    j = jdate_of(dt)
    y, m = (j.year + 1, 1) if j.month == 12 else (j.year, j.month + 1)
    return month_start_utc(y, m)


def period_label(key: str) -> str:
    y, m = parse_period(key)
    return f"{MONTHS_FA[m - 1]} {to_fa_digits(str(y))}"


def format_date(d: date | datetime) -> str:
    j = jdate_of(d)
    return to_fa_digits(f"{j.year:04d}/{j.month:02d}/{j.day:02d}")


def to_fa_digits(s: str) -> str:
    return s.translate(str.maketrans("0123456789", "۰۱۲۳۴۵۶۷۸۹"))


def days_in_period(key: str, months_per_period: int = 1) -> int:
    start, end = period_bounds_utc(key, months_per_period)
    return round((end - start).total_seconds() / 86400)
