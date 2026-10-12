from __future__ import annotations

from fastapi import APIRouter, Request, Response

from app.core.deps import DB
from app.modules.auth import service
from app.modules.auth.router_common import token_response
from app.modules.auth.schemas import (
    LoginOtpStartIn,
    LoginPasswordIn,
    OtpChallengeOut,
    OtpVerifyIn,
    SignupCompleteIn,
    SignupStartIn,
    SignupVerifyOut,
    TokenOut,
)

router = APIRouter(prefix="/auth", tags=["app:auth"])


@router.post("/signup/start", response_model=OtpChallengeOut)
def signup_start(body: SignupStartIn, request: Request, db: DB) -> OtpChallengeOut:
    return OtpChallengeOut(**service.signup_start(db, mobile_raw=body.mobile, subscription_raw=body.subscription_no,
                                                  referral_code=body.referral_code, device_id=body.device_id,
                                                  request=request))


@router.post("/signup/verify", response_model=SignupVerifyOut)
def signup_verify(body: OtpVerifyIn, request: Request, response: Response, db: DB) -> SignupVerifyOut:
    r = service.signup_verify(db, challenge_id=body.challenge_id, code=body.code, request=request)
    if r["status"] == "logged_in":
        return SignupVerifyOut(status="logged_in", tokens=token_response(r["tokens"], request, response))
    return SignupVerifyOut(status="verified", signup_token=r["signup_token"], terms_version=r["terms_version"])


@router.post("/signup/complete", response_model=TokenOut)
def signup_complete(body: SignupCompleteIn, request: Request, response: Response, db: DB) -> TokenOut:
    _user, pair = service.signup_complete(
        db, signup_token=body.signup_token, accept_terms=body.accept_terms, accept_privacy=body.accept_privacy,
        login_method=body.login_method, password=body.password, first_name=body.first_name,
        last_name=body.last_name, device_id=body.device_id, request=request)
    return token_response(pair, request, response)


@router.post("/login/otp/start", response_model=OtpChallengeOut)
def login_otp_start(body: LoginOtpStartIn, request: Request, db: DB) -> OtpChallengeOut:
    return OtpChallengeOut(**service.login_otp_start(db, mobile_raw=body.mobile, request=request))


@router.post("/login/otp/verify", response_model=TokenOut)
def login_otp_verify(body: OtpVerifyIn, request: Request, response: Response, db: DB) -> TokenOut:
    pair = service.login_otp_verify(db, challenge_id=body.challenge_id, code=body.code, device_id=body.device_id,
                                    request=request)
    return token_response(pair, request, response)


@router.post("/login/password", response_model=TokenOut)
def login_password(body: LoginPasswordIn, request: Request, response: Response, db: DB) -> TokenOut:
    pair = service.login_password(db, mobile_raw=body.mobile, password=body.password, device_id=body.device_id,
                                  request=request)
    return token_response(pair, request, response)
