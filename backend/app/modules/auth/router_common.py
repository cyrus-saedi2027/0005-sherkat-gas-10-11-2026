"""Token transport shared by both apps (ARCHITECTURE §4.2).

Browsers: refresh token lives in an httpOnly, SameSite=Strict cookie scoped to
/api/v1/auth — JavaScript can never read it. Native apps send `X-Client: native`
and get the refresh token in the body (stored in the OS keystore).
"""

from __future__ import annotations

from fastapi import APIRouter, Request, Response

from app.core.config import get_settings
from app.core.deps import DB
from app.modules.auth import service
from app.modules.auth.schemas import RefreshIn, TokenOut

COOKIE = "gz_rt"
COOKIE_PATH = "/api/v1/auth"

router = APIRouter(prefix="/auth", tags=["auth"])


def is_native(request: Request) -> bool:
    return request.headers.get("x-client", "").lower() == "native"


def token_response(pair: service.TokenPair, request: Request, response: Response) -> TokenOut:
    out = TokenOut(access_token=pair.access_token, expires_in=pair.expires_in, subject_type=pair.subject_type,
                   subject_id=pair.subject_id)
    if is_native(request):
        out.refresh_token = pair.refresh_token
    else:
        s = get_settings()
        response.set_cookie(COOKIE, pair.refresh_token, max_age=s.refresh_token_days * 86400, httponly=True,
                            secure=s.cookie_secure or s.is_prod, samesite="strict", path=COOKIE_PATH)
    return out


@router.post("/refresh", response_model=TokenOut)
def refresh(request: Request, response: Response, db: DB, body: RefreshIn | None = None) -> TokenOut:
    raw = (body.refresh_token if body and is_native(request) else None) or request.cookies.get(COOKIE)
    return token_response(service.refresh(db, raw, request), request, response)


@router.post("/logout", status_code=204)
def logout(request: Request, response: Response, db: DB, body: RefreshIn | None = None) -> Response:
    raw = (body.refresh_token if body else None) or request.cookies.get(COOKIE)
    service.logout(db, raw)
    response.delete_cookie(COOKIE, path=COOKIE_PATH)
    response.status_code = 204
    return response
