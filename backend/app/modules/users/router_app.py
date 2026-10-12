from __future__ import annotations

from fastapi import APIRouter, Request, Response

from app.core.deps import DB, CurrentUser
from app.modules.users import service
from app.modules.users.models import User
from app.modules.users.schemas import MeOut, PasswordSetIn, ProfileUpdate

router = APIRouter(prefix="/me", tags=["app:me"])


def _u(db, user) -> User:
    u = db.get(User, user.id)
    assert u is not None
    return u


@router.get("", response_model=MeOut)
def me(user: CurrentUser, db: DB) -> MeOut:
    return service.me_out(db, _u(db, user))


@router.patch("", response_model=MeOut)
def update(body: ProfileUpdate, user: CurrentUser, request: Request, db: DB) -> MeOut:
    return service.me_out(db, service.update_profile(db, _u(db, user), body, request))


@router.post("/login-method", status_code=204)
def login_method(body: PasswordSetIn, user: CurrentUser, request: Request, db: DB) -> Response:
    service.set_password(db, _u(db, user), body.password, body.login_method, request)
    return Response(status_code=204)
