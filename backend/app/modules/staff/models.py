from __future__ import annotations

from datetime import datetime

from sqlalchemy import JSON, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base, Timestamped


class StaffUser(Timestamped, Base):
    __tablename__ = "staff_users"
    username: Mapped[str] = mapped_column(String(64), unique=True)
    full_name: Mapped[str] = mapped_column(String(120))
    mobile_enc: Mapped[str | None] = mapped_column(String(512))
    mobile_bidx: Mapped[str | None] = mapped_column(String(64), index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    roles: Mapped[list[str]] = mapped_column(JSON, default=list)
    service_region_ids: Mapped[list[int]] = mapped_column(JSON, default=list)
    is_active: Mapped[bool] = mapped_column(default=True, index=True)
    otp_2fa_enabled: Mapped[bool] = mapped_column(default=False)
    failed_logins: Mapped[int] = mapped_column(default=0)
    locked_until: Mapped[datetime | None]
    last_login_at: Mapped[datetime | None]
    access_reviewed_at: Mapped[datetime | None]
    must_change_password: Mapped[bool] = mapped_column(default=False)
    last_assigned_at: Mapped[datetime | None]  # smart assignment tie-breaker (R38)
