from __future__ import annotations

from typing import Any

from sqlalchemy import JSON, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base, Timestamped


class AuditLog(Timestamped, Base):
    """Append-only trail of every state change made by staff/users/system (R35, R42)."""

    __tablename__ = "audit_logs"
    actor_type: Mapped[str] = mapped_column(String(16), index=True)  # staff | user | system
    actor_id: Mapped[int | None] = mapped_column(index=True)
    action: Mapped[str] = mapped_column(String(64), index=True)  # e.g. reading.approve
    entity_type: Mapped[str] = mapped_column(String(48), index=True)
    entity_id: Mapped[str | None] = mapped_column(String(64), index=True)
    before: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    after: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    ip: Mapped[str | None] = mapped_column(String(64))
    user_agent: Mapped[str | None] = mapped_column(String(300))
    request_id: Mapped[str | None] = mapped_column(String(64))


class LoginEvent(Timestamped, Base):
    __tablename__ = "login_events"
    actor_type: Mapped[str] = mapped_column(String(16), index=True)
    actor_id: Mapped[int | None] = mapped_column(index=True)
    identifier_masked: Mapped[str] = mapped_column(String(64))
    success: Mapped[bool] = mapped_column(index=True)
    reason: Mapped[str] = mapped_column(String(48))
    ip: Mapped[str | None] = mapped_column(String(64))
    user_agent: Mapped[str | None] = mapped_column(String(300))
