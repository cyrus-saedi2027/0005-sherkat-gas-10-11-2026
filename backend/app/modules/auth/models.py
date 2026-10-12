from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import JSON, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core import clock
from app.core.db import Base, Timestamped


class OtpChallenge(Base):
    __tablename__ = "otp_challenges"
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=lambda: uuid.uuid4().hex)
    mobile_bidx: Mapped[str] = mapped_column(String(64), index=True)
    purpose: Mapped[str] = mapped_column(String(16))  # signup | login | staff_2fa
    code_hash: Mapped[str] = mapped_column(String(64))
    expires_at: Mapped[datetime]
    attempts: Mapped[int] = mapped_column(default=0)
    consumed_at: Mapped[datetime | None]
    # A "decoy" challenge is issued for ineligible/unknown login numbers so the
    # response looks identical; it can never be verified.
    is_decoy: Mapped[bool] = mapped_column(default=False)
    ip: Mapped[str | None] = mapped_column(String(64))
    context: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(default=lambda: clock.now(), index=True)


class RefreshToken(Timestamped, Base):
    __tablename__ = "refresh_tokens"
    subject_type: Mapped[str] = mapped_column(String(8), index=True)
    subject_id: Mapped[int] = mapped_column(index=True)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True)
    family_id: Mapped[str] = mapped_column(String(32), index=True)
    expires_at: Mapped[datetime]
    revoked_at: Mapped[datetime | None]
    replaced_by_id: Mapped[int | None]
    ip: Mapped[str | None] = mapped_column(String(64))
    user_agent: Mapped[str | None] = mapped_column(String(300))
