from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class MeOut(BaseModel):
    id: int
    first_name: str | None
    last_name: str | None
    mobile_masked: str
    national_code_masked: str | None
    iban_masked: str | None
    subscription_no: str
    region_name: str | None
    login_method: str
    has_password: bool
    referral_code: str
    tier: str | None
    eligibility: str
    profile_completed: bool
    terms_version: str | None
    created_at: datetime


class ProfileUpdate(BaseModel):
    first_name: str | None = Field(default=None, min_length=2, max_length=80)
    last_name: str | None = Field(default=None, min_length=2, max_length=80)
    national_code: str | None = Field(default=None, max_length=14)
    iban: str | None = Field(default=None, max_length=34)


class PasswordSetIn(BaseModel):
    password: str = Field(max_length=128)
    login_method: str = Field(default="password", pattern="^(otp|password)$")


class AdminUserOut(BaseModel):
    id: int
    full_name: str | None
    mobile_masked: str
    subscription_no: str
    subscriber_id: int
    region_id: int | None
    region_name: str | None
    status: str
    tier: str | None
    eligibility: str
    profile_completed: bool
    created_at: datetime
    last_seen_at: datetime | None


class AdminUserDetail(AdminUserOut):
    national_code_masked: str | None
    iban_masked: str | None
    referral_code: str
    referred_by_user_id: int | None
    devices: int
    points_available: int
    points_pending: int
    points_suspended: int


class SuspendUserIn(BaseModel):
    suspend: bool
    reason: str = Field(min_length=3, max_length=300)
