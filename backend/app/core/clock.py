"""Single source of "now" so tests can freeze time (month-end releases, OTP expiry, rate windows)."""

from __future__ import annotations

from datetime import UTC, datetime

_frozen: datetime | None = None


def now() -> datetime:
    return _frozen if _frozen is not None else datetime.now(UTC)


def freeze(at: datetime | None) -> None:
    """Freeze (or with ``None`` unfreeze) the clock. Test-only."""
    global _frozen
    if at is not None and at.tzinfo is None:
        raise ValueError("freeze() needs a timezone-aware datetime")
    _frozen = at


def advance(**kwargs: float) -> datetime:
    from datetime import timedelta

    global _frozen
    if _frozen is None:
        raise RuntimeError("clock is not frozen")
    _frozen = _frozen + timedelta(**kwargs)
    return _frozen


def ensure_aware(dt: datetime) -> datetime:
    """SQLite returns naive datetimes; we always store UTC, so naive means UTC."""
    return dt.replace(tzinfo=UTC) if dt.tzinfo is None else dt
