from __future__ import annotations

from datetime import datetime

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base, Timestamped


class PointsRule(Timestamped, Base):
    """Editable points table (R22). `points` is per event, or per unit when per_unit (e.g. per % reduction)."""

    __tablename__ = "points_rules"
    event_type: Mapped[str] = mapped_column(String(40), unique=True)
    title_fa: Mapped[str] = mapped_column(String(120))
    points: Mapped[int]
    is_active: Mapped[bool] = mapped_column(default=True)
    per_unit: Mapped[bool] = mapped_column(default=False)
    monthly_cap_points: Mapped[int | None]
    updated_by: Mapped[int | None]


class PointsLedger(Timestamped, Base):
    """Every points movement, with date, reason and operation id (R22). Never updated except status."""

    __tablename__ = "points_ledger"
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    event_type: Mapped[str] = mapped_column(String(40), index=True)
    amount: Mapped[int]
    status: Mapped[str] = mapped_column(String(12), index=True)  # pending | available | suspended | reversed
    reason: Mapped[str] = mapped_column(String(300))
    ref_type: Mapped[str | None] = mapped_column(String(32))
    ref_id: Mapped[str | None] = mapped_column(String(64))
    # One reward per event (R24): the DB enforces it, not just the code path.
    idempotency_key: Mapped[str] = mapped_column(String(120), unique=True)
    period_key: Mapped[str | None] = mapped_column(String(7), index=True)
    available_at: Mapped[datetime | None] = mapped_column(index=True)
    created_by_staff_id: Mapped[int | None]
    suspended_reason: Mapped[str | None] = mapped_column(String(300))
    suspended_by: Mapped[int | None]
    suspended_at: Mapped[datetime | None]
    status_before_suspend: Mapped[str | None] = mapped_column(String(12))
