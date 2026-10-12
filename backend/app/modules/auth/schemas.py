from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class SignupStartIn(BaseModel):
    mobile: str = Field(min_length=10, max_length=20)
    subscription_no: str = Field(min_length=4, max_length=30)
    referral_code: str | None = Field(default=None, max_length=12)
    device_id: str | None = Field(default=None, max_length=64)


class OtpChallengeOut(BaseModel):
    challenge_id: str
    expires_in: int
    resend_in: int
    mobile_masked: str
    dev_code: str | None = None


class OtpVerifyIn(BaseModel):
    challenge_id: str = Field(min_length=8, max_length=40)
    code: str = Field(min_length=4, max_length=8)
    device_id: str | None = Field(default=None, max_length=64)


class SignupCompleteIn(BaseModel):
    signup_token: str = Field(max_length=2000)
    accept_terms: bool
    accept_privacy: bool
    login_method: Literal["otp", "password"] = "otp"
    password: str | None = Field(default=None, max_length=128)
    first_name: str | None = Field(default=None, max_length=80)
    last_name: str | None = Field(default=None, max_length=80)
    device_id: str | None = Field(default=None, max_length=64)


class LoginOtpStartIn(BaseModel):
    mobile: str = Field(min_length=10, max_length=20)


class LoginPasswordIn(BaseModel):
    mobile: str = Field(min_length=10, max_length=20)
    password: str = Field(min_length=1, max_length=128)
    device_id: str | None = Field(default=None, max_length=64)


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    subject_type: str
    subject_id: int
    # Present only for native clients (X-Client: native); browsers get an httpOnly cookie instead.
    refresh_token: str | None = None


class SignupVerifyOut(BaseModel):
    status: Literal["verified", "logged_in"]
    signup_token: str | None = None
    terms_version: str | None = None
    tokens: TokenOut | None = None


class RefreshIn(BaseModel):
    refresh_token: str | None = Field(default=None, max_length=200)


class StaffLoginIn(BaseModel):
    username: str = Field(min_length=3, max_length=64)
    password: str = Field(min_length=1, max_length=128)


class StaffLoginOut(BaseModel):
    otp_required: bool
    tokens: TokenOut | None = None
    challenge_id: str | None = None
    expires_in: int | None = None
    resend_in: int | None = None
    mobile_masked: str | None = None
    dev_code: str | None = None


class StaffMeOut(BaseModel):
    id: int
    username: str
    full_name: str
    roles: list[str]
    permissions: list[str]
    must_change_password: bool
    service_region_ids: list[int]
    otp_2fa_enabled: bool


class ChangePasswordIn(BaseModel):
    current_password: str = Field(max_length=128)
    new_password: str = Field(max_length=128)
