from __future__ import annotations

from datetime import date

from fastapi import APIRouter

from app.core.deps import DB, StaffCtx, require
from app.core.rbac import P
from app.modules.dashboard import service
from app.modules.dashboard.schemas import DashboardOut

router = APIRouter(prefix="/dashboard", tags=["admin:dashboard"])


@router.get("", response_model=DashboardOut)
def dashboard(db: DB, region_id: int | None = None, date_from: date | None = None, date_to: date | None = None,
              status: str | None = None, expert_id: int | None = None,
              staff: StaffCtx = require(P.DASHBOARD_VIEW)) -> DashboardOut:
    f = service.make_filters(db, region_id, date_from, date_to, status, expert_id)
    kpis, series, breakdown = service.build(db, staff, f)
    view = next((r for r in ("super_admin", "finance", "technician", "operator", "ambassador") if r in staff.roles), "staff")
    return DashboardOut(role_view=view, kpis=kpis, series=series, breakdown=breakdown)
