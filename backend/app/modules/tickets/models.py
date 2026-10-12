from __future__ import annotations

from datetime import datetime

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base, Timestamped


class Ticket(Timestamped, Base):
    """Support ticket (R32, R33, R39)."""

    __tablename__ = "tickets"
    tracking_code: Mapped[str] = mapped_column(String(20), unique=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    subject_key: Mapped[str] = mapped_column(String(16), index=True)
    title: Mapped[str] = mapped_column(String(160))
    status: Mapped[str] = mapped_column(String(20), default="open", index=True)
    priority: Mapped[str] = mapped_column(String(8), default="normal", index=True)
    assigned_unit: Mapped[str] = mapped_column(String(12), default="support", index=True)
    assignee_staff_id: Mapped[int | None] = mapped_column(ForeignKey("staff_users.id"), index=True)
    follow_up_at: Mapped[datetime | None] = mapped_column(index=True)
    rating: Mapped[int | None]
    rating_comment: Mapped[str | None] = mapped_column(String(500))
    rated_at: Mapped[datetime | None]
    closed_at: Mapped[datetime | None]
    last_customer_activity_at: Mapped[datetime | None]
    last_staff_activity_at: Mapped[datetime | None]


class TicketMessage(Timestamped, Base):
    __tablename__ = "ticket_messages"
    ticket_id: Mapped[int] = mapped_column(ForeignKey("tickets.id", ondelete="CASCADE"), index=True)
    author_type: Mapped[str] = mapped_column(String(8))  # user | staff | system
    author_id: Mapped[int | None]
    body: Mapped[str] = mapped_column(Text)
    is_internal: Mapped[bool] = mapped_column(default=False)  # internal note — never shown to the customer


class TicketAttachment(Timestamped, Base):
    __tablename__ = "ticket_attachments"
    message_id: Mapped[int] = mapped_column(ForeignKey("ticket_messages.id", ondelete="CASCADE"), index=True)
    file_id: Mapped[str] = mapped_column(ForeignKey("files.id"))
    kind: Mapped[str] = mapped_column(String(16), default="other")  # meter_photo | receipt | invoice | other


class TicketEvent(Timestamped, Base):
    __tablename__ = "ticket_events"
    ticket_id: Mapped[int] = mapped_column(ForeignKey("tickets.id", ondelete="CASCADE"), index=True)
    actor_type: Mapped[str] = mapped_column(String(8))
    actor_id: Mapped[int | None]
    field: Mapped[str] = mapped_column(String(20))  # status | priority | unit | assignee | follow_up
    old: Mapped[str | None] = mapped_column(String(80))
    new: Mapped[str | None] = mapped_column(String(80))
