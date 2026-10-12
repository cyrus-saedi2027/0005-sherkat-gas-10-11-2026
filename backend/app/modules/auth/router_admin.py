from __future__ import annotations

from fastapi import APIRouter, Request, Response

from app.core.deps import DB, CurrentStaff
from app.core.errors import AppError
from app.modules.auth import service
from app.modules.auth.router_common import token_response
from app.modules.auth.schemas import (
    ChangePasswordIn,
    OtpVerifyIn,
    StaffLoginIn,
    StaffLoginOut,
    StaffMeOut,
    TokenOut,
)
from app.modules.staff.models import StaffUser

router = APIRouter(prefix="/auth", tags=["admin:auth"])


@router.post("/login", response_model=StaffLoginOut)
def login(body: StaffLoginIn, request: Request, response: Response, db: DB) -> StaffLoginOut:
    r = service.staff_login(db, username=body.username, password=body.password, request=request)
    if r["otp_required"]:
        return StaffLoginOut(**r)
    return StaffLoginOut(otp_required=False, tokens=token_response(r["tokens"], request, response))


@router.post("/login/verify", response_model=TokenOut)
def login_verify(body: OtpVerifyIn, request: Request, response: Response, db: DB) -> TokenOut:
    return token_response(service.staff_login_verify(db, challenge_id=body.challenge_id, code=body.code, request=request),
                          request, response)


@router.get("/me", response_model=StaffMeOut)
def me(staff: CurrentStaff, db: DB) -> StaffMeOut:
    st = db.get(StaffUser, staff.id)
    if st is None:
        raise AppError("not_authenticated", "ابتدا وارد شوید.", 401)
    return StaffMeOut(**service.staff_profile(st))


@router.post("/change-password", status_code=204)
def change_password(body: ChangePasswordIn, staff: CurrentStaff, request: Request, db: DB) -> Response:
    st = db.get(StaffUser, staff.id)
    assert st is not None
    service.change_staff_password(db, st, body.current_password, body.new_password, request)
    return Response(status_code=204)
