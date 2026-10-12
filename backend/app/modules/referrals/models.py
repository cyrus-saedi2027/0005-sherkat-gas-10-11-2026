from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import JSON, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base, Timestamped


class Referral(Timestamped, Base):
    """Referral is recorded at signup but pays ONLY after the referee's first approved reading (R24)."""

    __tablename__ = "referrals"
    referrer_user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    referee_user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), unique=True)
    code_used: Mapped[str] = mapped_column(String(12))
    status: Mapped[str] = mapped_column(String(12), default="pending", index=True)
    # pending | rewarded | capped | suspicious | rejected
    qualified_at: Mapped[datetime | None]
    reason: Mapped[str | None] = mapped_column(String(300))
    signals: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    reviewed_by: Mapped[int | None]
    period_key: Mapped[str | None] = mapped_column(String(7), index=True)
