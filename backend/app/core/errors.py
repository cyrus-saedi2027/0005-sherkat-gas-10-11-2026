"""Uniform error contract: {"error": {"code", "message", "details"}} (ARCHITECTURE §4.1)."""

from __future__ import annotations

import logging
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

log = logging.getLogger("gazyar")

NOT_ELIGIBLE_FA = "اطلاعات واردشده برای این طرح قابل تأیید نیست؛ لطفاً با پشتیبانی تماس بگیرید."


class AppError(Exception):
    def __init__(self, code: str, message: str, status: int = 400, details: dict[str, Any] | None = None):
        super().__init__(code)
        self.code = code
        self.message = message
        self.status = status
        self.details = details or {}


def not_found(what: str = "مورد") -> AppError:
    return AppError("not_found", f"{what} پیدا نشد.", 404)


def forbidden(msg: str = "شما به این بخش دسترسی ندارید.") -> AppError:
    return AppError("forbidden", msg, 403)


def conflict(code: str, msg: str, details: dict[str, Any] | None = None) -> AppError:
    return AppError(code, msg, 409, details)


def bad_request(code: str, msg: str, details: dict[str, Any] | None = None) -> AppError:
    return AppError(code, msg, 400, details)


def _body(code: str, message: str, details: dict[str, Any] | None = None) -> dict[str, Any]:
    return {"error": {"code": code, "message": message, "details": details or {}}}


_FIELD_FA = {
    "missing": "این فیلد الزامی است.",
    "string_too_short": "مقدار واردشده خیلی کوتاه است.",
    "string_too_long": "مقدار واردشده خیلی طولانی است.",
    "greater_than_equal": "مقدار واردشده کمتر از حد مجاز است.",
    "less_than_equal": "مقدار واردشده بیشتر از حد مجاز است.",
    "greater_than": "مقدار واردشده کمتر از حد مجاز است.",
    "less_than": "مقدار واردشده بیشتر از حد مجاز است.",
    "int_parsing": "یک عدد معتبر وارد کنید.",
    "float_parsing": "یک عدد معتبر وارد کنید.",
    "date_from_datetime_parsing": "تاریخ معتبر نیست.",
    "date_parsing": "تاریخ معتبر نیست.",
    "literal_error": "مقدار انتخاب‌شده معتبر نیست.",
    "enum": "مقدار انتخاب‌شده معتبر نیست.",
    "bool_parsing": "مقدار معتبر نیست.",
    "too_long": "تعداد موارد بیش از حد مجاز است.",
}


def install(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def _app_error(_req: Request, exc: AppError) -> JSONResponse:
        headers = {"Retry-After": str(exc.details["retry_after"])} if "retry_after" in exc.details else None
        return JSONResponse(_body(exc.code, exc.message, exc.details), status_code=exc.status, headers=headers)

    @app.exception_handler(RequestValidationError)
    async def _validation(_req: Request, exc: RequestValidationError) -> JSONResponse:
        fields: dict[str, str] = {}
        for err in exc.errors():
            loc = [str(p) for p in err.get("loc", ()) if p not in ("body", "query", "path")]
            key = ".".join(loc) or "_"
            msg = err.get("msg", "")
            # Custom validators raise ValueError with a Persian message; keep it.
            if err.get("type") == "value_error" and msg.startswith("Value error, "):
                fields[key] = msg.removeprefix("Value error, ")
            else:
                fields[key] = _FIELD_FA.get(err.get("type", ""), "مقدار واردشده معتبر نیست.")
        return JSONResponse(_body("validation_error", "اطلاعات واردشده کامل یا معتبر نیست.", {"fields": fields}), status_code=422)

    @app.exception_handler(StarletteHTTPException)
    async def _http(_req: Request, exc: StarletteHTTPException) -> JSONResponse:
        mapping = {
            404: ("not_found", "مسیر درخواستی پیدا نشد."),
            405: ("method_not_allowed", "این عملیات مجاز نیست."),
            401: ("not_authenticated", "ابتدا وارد حساب کاربری شوید."),
            403: ("forbidden", "شما به این بخش دسترسی ندارید."),
            413: ("payload_too_large", "حجم درخواست بیش از حد مجاز است."),
        }
        code, msg = mapping.get(exc.status_code, ("http_error", "درخواست قابل انجام نیست."))
        if isinstance(exc.detail, dict) and "code" in exc.detail:
            code, msg = exc.detail["code"], exc.detail.get("message", msg)
        return JSONResponse(_body(code, msg), status_code=exc.status_code, headers=getattr(exc, "headers", None))

    @app.exception_handler(Exception)
    async def _unhandled(req: Request, exc: Exception) -> JSONResponse:
        log.exception("unhandled error on %s %s", req.method, req.url.path)
        return JSONResponse(_body("server_error", "خطای داخلی سرور؛ لطفاً دوباره تلاش کنید."), status_code=500)
