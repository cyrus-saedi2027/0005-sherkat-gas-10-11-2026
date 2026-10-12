from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import JSON, Float, ForeignKey, Index, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base, Timestamped


class MeterReading(Timestamped, Base):
    """One revision of a subscriber's reading for a period (ARCHITECTURE §3.4).

    Revisions never overwrite each other: a correction or review request adds a
    new row (revision+1) and flips `is_current`, so the full history stays
    auditable and the points key (per subscriber+period) prevents double pay (R13).
    """

    __tablename__ = "meter_readings"
    __table_args__ = (
        UniqueConstraint("subscriber_id", "period_key", "revision"),
        Index("ix_meter_readings_queue", "status", "created_at"),
    )
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    subscriber_id: Mapped[int] = mapped_column(ForeignKey("subscribers.id"), index=True)
    period_key: Mapped[str] = mapped_column(String(7), index=True)
    revision: Mapped[int] = mapped_column(default=1)
    kind: Mapped[str] = mapped_column(String(16), default="initial")  # initial | correction | review_request
    parent_id: Mapped[int | None] = mapped_column(ForeignKey("meter_readings.id"))
    is_current: Mapped[bool] = mapped_column(default=True, index=True)
    input_method: Mapped[str] = mapped_column(String(8), default="photo")  # photo | manual
    declared_value: Mapped[float] = mapped_column(Float)
    reading_date: Mapped[date]
    photo_file_id: Mapped[str | None] = mapped_column(ForeignKey("files.id"))
    user_note: Mapped[str | None] = mapped_column(String(500))
    status: Mapped[str] = mapped_column(String(20), default="pending", index=True)
    approved_value: Mapped[float | None] = mapped_column(Float)
    consumption_m3: Mapped[float | None] = mapped_column(Float)
    baseline_m3: Mapped[float | None] = mapped_column(Float)
    reduction_pct: Mapped[float | None] = mapped_column(Float)
    flags: Mapped[list[str]] = mapped_column(JSON, default=list)
    reviewer_id: Mapped[int | None] = mapped_column(ForeignKey("staff_users.id"))
    reviewed_at: Mapped[datetime | None]
    reason_code: Mapped[str | None] = mapped_column(String(40))
    review_note: Mapped[str | None] = mapped_column(Text)
    # Soft claim so two operators don't review the same item at once.
    claimed_by: Mapped[int | None]
    claimed_at: Mapped[datetime | None]


class ReadingEvent(Timestamped, Base):
    """Per-reading change log shown in the panel (R29: log of changes)."""

    __tablename__ = "reading_events"
    reading_id: Mapped[int] = mapped_column(ForeignKey("meter_readings.id", ondelete="CASCADE"), index=True)
    actor_type: Mapped[str] = mapped_column(String(8))
    actor_id: Mapped[int | None]
    action: Mapped[str] = mapped_column(String(24))
    from_status: Mapped[str | None] = mapped_column(String(20))
    to_status: Mapped[str | None] = mapped_column(String(20))
    old_value: Mapped[float | None] = mapped_column(Float)
    new_value: Mapped[float | None] = mapped_column(Float)
    reason: Mapped[str | None] = mapped_column(String(500))
