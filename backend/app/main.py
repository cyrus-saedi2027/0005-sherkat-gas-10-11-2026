"""ASGI app factory."""

from __future__ import annotations

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app import models  # noqa: F401  (populate metadata)
from app.api import build_router
from app.core import errors
from app.core.config import get_settings
from app.core.middleware import BodySizeLimit, RequestContext


def create_app() -> FastAPI:
    s = get_settings()
    s.check_prod()
    logging.basicConfig(level=logging.INFO)
    app = FastAPI(
        title="Gazyar API",
        version="1.0.0",
        description="API اپلیکیشن کاربر و پنل مدیریت گازیار",
        docs_url=None if s.is_prod else "/docs",
        redoc_url=None,
        openapi_url=None if s.is_prod else "/openapi.json",
    )
    errors.install(app)
    app.add_middleware(RequestContext)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=s.cors_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
        allow_headers=["Authorization", "Content-Type", "X-Request-Id", "X-Client", "Accept-Language"],
        expose_headers=["X-Request-Id", "Retry-After", "Content-Disposition"],
        max_age=600,
    )
    app.add_middleware(BodySizeLimit)
    app.include_router(build_router())

    if s.run_scheduler:
        from app.core.scheduler import start

        start()
    return app


app = create_app()
