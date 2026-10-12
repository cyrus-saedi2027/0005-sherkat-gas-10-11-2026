from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import JSON, Float, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base, Timestamped


class Case(Timestamped, Base):
    """Technical evaluation file (پرونده) — ARCHITECTURE §3.5, R14–R19, R30, R38."""

    __tablename__ = "cases"
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    subscriber_id: Mapped[int] = mapped_column(ForeignKey("subscribers.id"), index=True)
    region_id: Mapped[int | None] = mapped_column(ForeignKey("regions.id"), index=True)
    status: Mapped[str] = mapped_column(String(24), default="new", index=True)
    tier: Mapped[str | None] = mapped_column(String(12), index=True)
    suggested_tier: Mapped[str | None] = mapped_column(String(12))
    tier_reason: Mapped[str | None] = mapped_column(String(500))
    needs_field_visit: Mapped[bool | None]
    ambassador_id: Mapped[int | None] = mapped_column(ForeignKey("staff_users.id"), index=True)
    technician_id: Mapped[int | None] = mapped_column(ForeignKey("staff_users.id"))
    assignment_method: Mapped[str | None] = mapped_column(String(8))
    assigned_at: Mapped[datetime | None]
    opened_reason: Mapped[str] = mapped_column(String(32), default="first_approved_reading")
    opened_by_reading_id: Mapped[int | None] = mapped_column(ForeignKey("meter_readings.id"))
    priority: Mapped[str] = mapped_column(String(8), default="normal")
    executed: Mapped[bool] = mapped_column(default=False)
    completed_at: Mapped[datetime | None]
    closed_reason: Mapped[str | None] = mapped_column(String(300))


class CaseCall(Timestamped, Base):
    __tablename__ = "case_calls"
    case_id: Mapped[int] = mapped_column(ForeignKey("cases.id", ondelete="CASCADE"), index=True)
    staff_id: Mapped[int] = mapped_column(ForeignKey("staff_users.id"))
    called_at: Mapped[datetime]
    outcome: Mapped[str] = mapped_column(String(16))  # reached | no_answer | wrong_number | callback
    note: Mapped[str | None] = mapped_column(String(1000))
    next_call_at: Mapped[datetime | None]


class CaseChecklist(Timestamped, Base):
    """Checklist from R16: area, residents, heating equipment, insulation, seals, chimneys."""

    __tablename__ = "case_checklists"
    case_id: Mapped[int] = mapped_column(ForeignKey("cases.id", ondelete="CASCADE"), unique=True)
    floor_area_m2: Mapped[float | None] = mapped_column(Float)
    built_area_m2: Mapped[float | None] = mapped_column(Float)
    residents_count: Mapped[int | None]
    building_type: Mapped[str | None] = mapped_column(String(16))  # apartment | villa | other
    heating_equipment: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list)
    insulation: Mapped[str | None] = mapped_column(String(12))  # none | partial | full
    window_seals: Mapped[str | None] = mapped_column(String(12))  # none | poor | good
    chimney_status: Mapped[str | None] = mapped_column(String(16))  # ok | needs_repair | blocked | none
    notes: Mapped[str | None] = mapped_column(Text)
    completed_by: Mapped[int | None] = mapped_column(ForeignKey("staff_users.id"))


class CaseVisit(Timestamped, Base):
    __tablename__ = "case_visits"
    case_id: Mapped[int] = mapped_column(ForeignKey("cases.id", ondelete="CASCADE"), index=True)
    ambassador_id: Mapped[int] = mapped_column(ForeignKey("staff_users.id"), index=True)
    scheduled_start: Mapped[datetime] = mapped_column(index=True)
    scheduled_end: Mapped[datetime]
    status: Mapped[str] = mapped_column(String(12), default="scheduled")  # scheduled | done | missed | cancelled
    note: Mapped[str | None] = mapped_column(String(1000))


class CasePhoto(Timestamped, Base):
    __tablename__ = "case_photos"
    case_id: Mapped[int] = mapped_column(ForeignKey("cases.id", ondelete="CASCADE"), index=True)
    file_id: Mapped[str] = mapped_column(ForeignKey("files.id"))
    phase: Mapped[str] = mapped_column(String(8))  # before | after
    caption: Mapped[str | None] = mapped_column(String(300))
    uploaded_by: Mapped[int | None]


class CaseEstimate(Timestamped, Base):
    __tablename__ = "case_estimates"
    case_id: Mapped[int] = mapped_column(ForeignKey("cases.id", ondelete="CASCADE"), index=True)
    items: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list)  # [{title, qty, unit_cost_rial}]
    total_cost_rial: Mapped[int]
    free_cap_rial: Mapped[int]
    subscriber_share_pct: Mapped[int]
    subscriber_share_rial: Mapped[int]
    program_share_rial: Mapped[int]
    status: Mapped[str] = mapped_column(String(10), default="sent")  # sent | accepted | declined | superseded
    created_by: Mapped[int | None]
    responded_at: Mapped[datetime | None]
    note: Mapped[str | None] = mapped_column(String(1000))


class CaseEvent(Timestamped, Base):
    __tablename__ = "case_events"
    case_id: Mapped[int] = mapped_column(ForeignKey("cases.id", ondelete="CASCADE"), index=True)
    actor_type: Mapped[str] = mapped_column(String(8))
    actor_id: Mapped[int | None]
    action: Mapped[str] = mapped_column(String(32))
    from_status: Mapped[str | None] = mapped_column(String(24))
    to_status: Mapped[str | None] = mapped_column(String(24))
    note: Mapped[str | None] = mapped_column(String(1000))
