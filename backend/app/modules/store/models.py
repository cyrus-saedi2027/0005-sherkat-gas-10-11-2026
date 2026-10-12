from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import JSON, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base, Timestamped


class RewardCategory(Timestamped, Base):
    __tablename__ = "reward_categories"
    key: Mapped[str] = mapped_column(String(24), unique=True)
    title: Mapped[str] = mapped_column(String(80))
    icon: Mapped[str] = mapped_column(String(24), default="gift")
    sort: Mapped[int] = mapped_column(default=0)
    is_active: Mapped[bool] = mapped_column(default=True)


class RewardItem(Timestamped, Base):
    """Something points can buy (R25). kind: product | discount | cash | donation."""

    __tablename__ = "reward_items"
    category_id: Mapped[int] = mapped_column(ForeignKey("reward_categories.id"), index=True)
    title: Mapped[str] = mapped_column(String(160))
    description: Mapped[str] = mapped_column(Text, default="")
    image_file_id: Mapped[str | None] = mapped_column(String(32))
    kind: Mapped[str] = mapped_column(String(10), index=True)
    points_cost: Mapped[int]  # for cash: points per unit is the rial rate; cost here is the minimum
    rial_value: Mapped[int] = mapped_column(default=0)
    stock: Mapped[int | None]
    is_active: Mapped[bool] = mapped_column(default=True, index=True)
    charity_name: Mapped[str | None] = mapped_column(String(160))
    needs_address: Mapped[bool] = mapped_column(default=False)
    sort: Mapped[int] = mapped_column(default=0)


class Redemption(Timestamped, Base):
    """A request to spend points. Points are reserved at submit; refunded if rejected (R21)."""

    __tablename__ = "redemptions"
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    item_id: Mapped[int | None] = mapped_column(ForeignKey("reward_items.id"))
    kind: Mapped[str] = mapped_column(String(10), index=True)
    title: Mapped[str] = mapped_column(String(160))
    points: Mapped[int]
    rial_value: Mapped[int]
    status: Mapped[str] = mapped_column(String(12), default="submitted", index=True)
    # submitted | approved | rejected | fulfilled | cancelled
    fraud_signals: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    iban_enc: Mapped[str | None] = mapped_column(String(512))
    delivery_address: Mapped[str | None] = mapped_column(String(500))
    user_note: Mapped[str | None] = mapped_column(String(500))
    finance_note: Mapped[str | None] = mapped_column(String(500))
    reviewed_by: Mapped[int | None]
    reviewed_at: Mapped[datetime | None]
    fulfilled_at: Mapped[datetime | None]
    payment_ref: Mapped[str | None] = mapped_column(String(80))
    spend_entry_id: Mapped[int | None]
    refund_entry_id: Mapped[int | None]
