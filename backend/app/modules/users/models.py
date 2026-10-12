from __future__ import annotations

from datetime import datetime

from sqlalchemy import ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base, Timestamped


class User(Timestamped, Base):
    """A subscriber's app account. One account per subscriber (R24)."""

    __tablename__ = "users"
    subscriber_id: Mapped[int] = mapped_column(ForeignKey("subscribers.id"), unique=True)
    mobile_enc: Mapped[str] = mapped_column(String(512))
    mobile_bidx: Mapped[str] = mapped_column(String(64), unique=True)
    national_code_enc: Mapped[str | None] = mapped_column(String(512))
    national_code_bidx: Mapped[str | None] = mapped_column(String(64), unique=True)
    first_name: Mapped[str | None] = mapped_column(String(80))
    last_name: Mapped[str | None] = mapped_column(String(80))
    iban_enc: Mapped[str | None] = mapped_column(String(512))
    password_hash: Mapped[str | None] = mapped_column(String(255))
    login_method: Mapped[str] = mapped_column(String(10), default="otp")  # otp | password
    terms_version: Mapped[str | None] = mapped_column(String(16))
    terms_accepted_at: Mapped[datetime | None]
    privacy_accepted_at: Mapped[datetime | None]
    referral_code: Mapped[str] = mapped_column(String(12), unique=True)
    referred_by_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    status: Mapped[str] = mapped_column(String(12), default="active", index=True)  # active | suspended
    eligibility: Mapped[str] = mapped_column(String(16), default="eligible")  # eligible | below_threshold
    tier: Mapped[str | None] = mapped_column(String(12), index=True)
    profile_completed_at: Mapped[datetime | None]
    failed_logins: Mapped[int] = mapped_column(default=0)
    locked_until: Mapped[datetime | None]
    last_seen_at: Mapped[datetime | None]


class UserDevice(Timestamped, Base):
    __tablename__ = "user_devices"
    __table_args__ = (UniqueConstraint("user_id", "device_id"),)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    device_id: Mapped[str] = mapped_column(String(64), index=True)
    platform: Mapped[str | None] = mapped_column(String(24))
    user_agent: Mapped[str | None] = mapped_column(String(300))
    last_seen_at: Mapped[datetime | None]
