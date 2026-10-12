from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel


class ReferralOut(BaseModel):
    id: int
    referrer_user_id: int
    referrer_name: str | None
    referee_user_id: int
    referee_name: str | None
    code_used: str
    status: str
    reason: str | None
    signals: dict[str, Any]
    qualified_at: datetime | None
    created_at: datetime


class MyReferralOut(BaseModel):
    id: int
    referee_name: str
    status: str
    created_at: datetime
    qualified_at: datetime | None


class MyReferralsOut(BaseModel):
    code: str
    share_text: str
    items: list[MyReferralOut]
    rewarded: int
    pending: int
    monthly_cap: int
    points_per_referral: int
