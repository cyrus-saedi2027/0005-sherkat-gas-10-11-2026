from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


class CategoryOut(BaseModel):
    id: int
    key: str
    title: str
    icon: str
    sort: int
    is_active: bool


class ItemOut(BaseModel):
    id: int
    category_id: int
    category_key: str | None = None
    title: str
    description: str
    image_url: str | None
    kind: str
    points_cost: int
    rial_value: int
    stock: int | None
    is_active: bool
    charity_name: str | None
    needs_address: bool


class ItemIn(BaseModel):
    category_id: int
    title: str = Field(min_length=2, max_length=160)
    description: str = Field(default="", max_length=5000)
    image_file_id: str | None = Field(default=None, max_length=32)
    kind: Literal["product", "discount", "cash", "donation"]
    points_cost: int = Field(ge=1, le=10_000_000)
    rial_value: int = Field(default=0, ge=0, le=100_000_000_000)
    stock: int | None = Field(default=None, ge=0, le=1_000_000)
    is_active: bool = True
    charity_name: str | None = Field(default=None, max_length=160)
    needs_address: bool = False
    sort: int = 0


class RedeemIn(BaseModel):
    kind: Literal["item", "cash"] = "item"
    item_id: int | None = None
    points: int | None = Field(default=None, ge=1, le=100_000_000)
    delivery_address: str | None = Field(default=None, max_length=500)
    note: str | None = Field(default=None, max_length=500)


class RedemptionOut(BaseModel):
    id: int
    kind: str
    title: str
    points: int
    rial_value: int
    status: str
    delivery_address: str | None
    user_note: str | None
    finance_note: str | None
    payment_ref: str | None
    created_at: datetime
    reviewed_at: datetime | None
    fulfilled_at: datetime | None


class AdminRedemptionOut(RedemptionOut):
    user_id: int
    user_name: str | None
    subscription_no: str | None
    iban_masked: str | None
    fraud_signals: dict[str, Any]
    available_balance: int
    reviewed_by_name: str | None


class StoreOut(BaseModel):
    categories: list[CategoryOut]
    items: list[ItemOut]
    available_points: int
    pending_points: int
    rial_rate: int
    min_cash_points: int
    has_iban: bool
    window_open: bool
