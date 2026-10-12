"""Request id, body-size ceiling, security headers (R36, OWASP)."""

from __future__ import annotations

import uuid

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from app.core.config import get_settings

_SEC_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "strict-origin-when-cross-origin",
    "Permissions-Policy": "geolocation=(), microphone=(), camera=()",
    "Cross-Origin-Opener-Policy": "same-origin",
}


class RequestContext(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        rid = request.headers.get("x-request-id", "")[:64] or uuid.uuid4().hex
        request.state.request_id = rid
        response = await call_next(request)
        response.headers["X-Request-Id"] = rid
        for k, v in _SEC_HEADERS.items():
            response.headers.setdefault(k, v)
        if request.url.path.startswith("/api/"):
            response.headers.setdefault("Cache-Control", "no-store")
            response.headers.setdefault("Content-Security-Policy", "default-src 'none'; frame-ancestors 'none'")
        if get_settings().is_prod:
            response.headers.setdefault("Strict-Transport-Security", "max-age=31536000; includeSubDomains")
        return response


class BodySizeLimit:
    """Reject oversized bodies while streaming — before they are buffered in memory.

    Content-Length is checked first, then actual bytes (chunked uploads have no length).
    """

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        s = get_settings()
        headers = {k.decode().lower(): v.decode() for k, v in scope.get("headers", [])}
        ctype = headers.get("content-type", "")
        limit = s.max_upload_body_bytes if ctype.startswith("multipart/") else s.max_json_body_bytes
        declared = headers.get("content-length")
        if declared and declared.isdigit() and int(declared) > limit:
            await _too_large(scope, receive, send)
            return
        seen = 0

        async def limited_receive() -> Message:
            nonlocal seen
            msg = await receive()
            if msg["type"] == "http.request":
                seen += len(msg.get("body", b""))
                if seen > limit:
                    raise _TooLarge
            return msg

        try:
            await self.app(scope, limited_receive, send)
        except _TooLarge:
            await _too_large(scope, receive, send)


class _TooLarge(Exception):
    pass


async def _too_large(scope: Scope, receive: Receive, send: Send) -> None:
    resp = JSONResponse({"error": {"code": "payload_too_large", "message": "حجم درخواست بیش از حد مجاز است.", "details": {}}},
                        status_code=413)
    await resp(scope, receive, send)
