"""Single registry of routers (ARCHITECTURE §5)."""

from __future__ import annotations

import importlib

from fastapi import APIRouter

# (module, has_app_router, has_admin_router)
MODULES: list[tuple[str, bool, bool]] = [
    ("auth", True, True),
    ("staff", False, True),
    ("audit", False, True),
    ("settings", False, True),
    ("regions", True, True),
    ("subscribers", False, True),
    ("users", True, True),
    ("readings", True, True),
    ("notifications", True, True),
    ("points", True, True),
    ("dashboard", False, True),
    # stage 2
    ("cases", True, True),
    ("referrals", True, True),
    ("content", True, True),
    ("analytics", True, False),
]


def build_router() -> APIRouter:
    root = APIRouter(prefix="/api/v1")
    from app.modules.auth.router_common import router as auth_common
    from app.modules.files.router import router as files_router

    root.include_router(auth_common)
    root.include_router(files_router)
    app_r = APIRouter(prefix="/app")
    admin_r = APIRouter(prefix="/admin")
    for name, has_app, has_admin in MODULES:
        if has_app:
            app_r.include_router(importlib.import_module(f"app.modules.{name}.router_app").router)
        if has_admin:
            admin_r.include_router(importlib.import_module(f"app.modules.{name}.router_admin").router)
    root.include_router(app_r)
    root.include_router(admin_r)

    @root.get("/health", tags=["meta"])
    def health() -> dict[str, str]:
        return {"status": "ok"}

    return root
