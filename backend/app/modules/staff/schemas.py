from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field, field_validator

from app.core.rbac import Role


class StaffOut(BaseModel):
    id: int
    username: str
    full_name: str
    mobile_masked: str
    roles: list[str]
    service_region_ids: list[int]
    is_active: bool
    otp_2fa_enabled: bool
    locked: bool
    last_login_at: datetime | None
    access_reviewed_at: datetime | None
    created_at: datetime


def _check_roles(v: list[str] | None) -> list[str] | None:
    if v is None:
        return v
    allowed = {r.value for r in Role}
    if any(r not in allowed for r in v):
        raise ValueError("نقش انتخاب‌شده معتبر نیست.")
    return sorted(set(v))


class StaffCreate(BaseModel):
    username: str = Field(min_length=3, max_length=64, pattern=r"^[a-zA-Z0-9_.\-]+$")
    full_name: str = Field(min_length=2, max_length=120)
    mobile: str | None = Field(default=None, max_length=20)
    password: str = Field(min_length=8, max_length=128)
    roles: list[str] = Field(min_length=1, max_length=5)
    service_region_ids: list[int] = Field(default_factory=list, max_length=200)
    otp_2fa_enabled: bool = False

    _roles = field_validator("roles")(_check_roles)


class StaffUpdate(BaseModel):
    full_name: str | None = Field(default=None, min_length=2, max_length=120)
    mobile: str | None = Field(default=None, max_length=20)
    roles: list[str] | None = Field(default=None, min_length=1, max_length=5)
    service_region_ids: list[int] | None = Field(default=None, max_length=200)
    is_active: bool | None = None
    otp_2fa_enabled: bool | None = None

    _roles = field_validator("roles")(_check_roles)


class ResetPasswordIn(BaseModel):
    new_password: str = Field(min_length=8, max_length=128)


class RoleOut(BaseModel):
    id: str
    title_fa: str
    permissions: list[str]


class AccessReviewIn(BaseModel):
    notes: str = Field(default="", max_length=1000)
