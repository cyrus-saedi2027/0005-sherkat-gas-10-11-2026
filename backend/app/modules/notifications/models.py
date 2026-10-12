from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base, Timestamped


class Notification(Timestamped, Base):
    __tablename__ = "notifications"
    recipient_type: Mapped[str] = mapped_column(String(8), index=True)  # user | staff
    recipient_id: Mapped[int] = mapped_column(index=True)
    kind: Mapped[str] = mapped_column(String(40), index=True)
    title: Mapped[str] = mapped_column(String(160))
    body: Mapped[str] = mapped_column(Text, default="")
    data: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)  # e.g. {"route": "/readings/12"}
    read_at: Mapped[datetime | None]
    broadcast_id: Mapped[int | None] = mapped_column(index=True)


class SmsOutbox(Timestamped, Base):
    """Queued SMS. Sending is asynchronous so no API response time depends on the SMS provider
    (otherwise response latency would reveal whether an OTP was really sent — R09)."""

    __tablename__ = "sms_outbox"
    mobile_enc: Mapped[str] = mapped_column(String(512))
    text: Mapped[str] = mapped_column(String(700))
    purpose: Mapped[str] = mapped_column(String(24), index=True)  # otp | notify | broadcast
    status: Mapped[str] = mapped_column(String(12), default="queued", index=True)  # queued | sent | failed
    attempts: Mapped[int] = mapped_column(default=0)
    provider_ref: Mapped[str | None] = mapped_column(String(80))
    error: Mapped[str | None] = mapped_column(String(300))
    sent_at: Mapped[datetime | None]
    # OTP texts contain the code — wiped after sending so the DB never keeps live codes.
    sensitive: Mapped[bool] = mapped_column(default=False)


class Broadcast(Timestamped, Base):
    """Group message to a segment of subscribers (R46: send messages & notifications)."""

    __tablename__ = "broadcasts"
    title: Mapped[str] = mapped_column(String(160))
    body: Mapped[str] = mapped_column(Text, default="")
    channels: Mapped[list[str]] = mapped_column(JSON, default=list)  # in_app | sms
    segment: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)  # {region_ids, tiers, eligibility, status}
    route: Mapped[str | None] = mapped_column(String(120))
    status: Mapped[str] = mapped_column(String(10), default="sent")
    recipients: Mapped[int] = mapped_column(default=0)
    created_by: Mapped[int]
