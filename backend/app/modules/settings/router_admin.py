from __future__ import annotations

from fastapi import APIRouter, Request

from app.core.deps import DB, StaffCtx, require
from app.core.rbac import P
from app.modules.settings import service
from app.modules.settings.schemas import SettingOut, SettingsUpdate

router = APIRouter(prefix="/settings", tags=["admin:settings"])


@router.get("", response_model=list[SettingOut])
def list_settings(db: DB, staff: StaffCtx = require(P.SETTINGS_VIEW)) -> list[SettingOut]:
    return service.list_settings(db, staff.perms)


@router.put("", response_model=list[SettingOut])
def update_settings(body: SettingsUpdate, request: Request, db: DB, staff: StaffCtx = require(P.SETTINGS_VIEW)) -> list[SettingOut]:
    # Per-key permission is enforced in the service (finance keys need settings.finance_edit).
    service.update_settings(db, body.values, staff.actor, staff.perms, request)
    return service.list_settings(db, staff.perms)
