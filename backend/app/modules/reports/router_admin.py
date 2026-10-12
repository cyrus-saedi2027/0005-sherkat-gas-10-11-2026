from __future__ import annotations

from datetime import date, datetime
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import Response
from pydantic import BaseModel, Field
from sqlalchemy import func, select

from app.core import audit, clock, jalali
from app.core.deps import DB, StaffCtx, require
from app.core.pagination import Page, PageParams, page_params
from app.core.rbac import P
from app.modules.files import service as files
from app.modules.reports import service
from app.modules.reports.models import ReportSnapshot

router = APIRouter(prefix="/reports", tags=["admin:reports"])
XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


class ColumnOut(BaseModel):
    key: str
    title: str
    type: str


class TableOut(BaseModel):
    key: str
    title: str
    columns: list[ColumnOut]
    rows: list[dict[str, Any]]
    summary: dict[str, Any]
    chart: dict[str, Any] | None


class SnapshotIn(BaseModel):
    region_id: int | None = None
    date_from: date | None = None
    date_to: date | None = None
    tier: str | None = Field(default=None, pattern="^(no_cost|low_cost|high_cost)$")
    expert_id: int | None = None
    note: str | None = Field(default=None, max_length=300)


class SnapshotOut(BaseModel):
    id: int
    report_key: str
    version: int
    title: str
    params: dict[str, Any]
    summary: dict[str, Any]
    row_count: int
    xlsx_url: str | None
    csv_url: str | None
    created_by: int
    note: str | None
    created_at: datetime


def params(region_id: int | None = None, date_from: date | None = None, date_to: date | None = None,
           tier: Annotated[str | None, Query(pattern="^(no_cost|low_cost|high_cost)$")] = None,
           expert_id: int | None = None) -> service.Params:
    return service.Params(region_id, date_from, date_to, tier, expert_id)


def _snap_out(s: ReportSnapshot) -> SnapshotOut:
    return SnapshotOut(id=s.id, report_key=s.report_key, version=s.version, title=s.title, params=s.params, summary=s.summary,
                       row_count=s.row_count, xlsx_url=files.url(s.xlsx_file_id), csv_url=files.url(s.csv_file_id),
                       created_by=s.created_by, note=s.note, created_at=s.created_at)


@router.get("")
def catalog(_s: StaffCtx = require(P.REPORTS_VIEW)) -> list[dict[str, str]]:
    return [{"key": d.key, "title": d.title, "description": d.description} for d in service.REPORTS.values()]


@router.get("/snapshots", response_model=Page[SnapshotOut])
def snapshots(db: DB, p: PageParams = Depends(page_params), report_key: str | None = None,
              _s: StaffCtx = require(P.REPORTS_VIEW)) -> Page[SnapshotOut]:
    stmt = select(ReportSnapshot).order_by(ReportSnapshot.id.desc())
    if report_key:
        stmt = stmt.where(ReportSnapshot.report_key == report_key)
    total = int(db.scalar(select(func.count()).select_from(stmt.order_by(None).subquery())) or 0)
    return Page(items=[_snap_out(s) for s in db.scalars(stmt.limit(p.size).offset(p.offset)).all()], total=total, page=p.page, size=p.size)


@router.get("/{key}", response_model=TableOut)
def view(key: str, db: DB, prm: service.Params = Depends(params), _s: StaffCtx = require(P.REPORTS_VIEW)) -> TableOut:
    t = service.run(db, key, prm)
    return TableOut(key=key, title=t.title, columns=[ColumnOut(**c.__dict__) for c in t.columns], rows=t.rows,
                    summary=t.summary, chart=t.chart)


@router.get("/{key}/export")
def export(key: str, request: Request, db: DB, fmt: Annotated[str, Query(alias="format", pattern="^(xlsx|csv)$")] = "xlsx",
           prm: service.Params = Depends(params), staff: StaffCtx = require(P.REPORTS_EXPORT)) -> Response:
    t = service.run(db, key, prm)
    audit.record(db, staff.actor, "report.export", "report", key, None, {"format": fmt, "rows": len(t.rows)}, request)
    stamp = jalali.period_key(clock.now())
    if fmt == "csv":
        return Response(service.to_csv(t), media_type="text/csv; charset=utf-8",
                        headers={"Content-Disposition": f'attachment; filename="gazyar-{key}-{stamp}.csv"'})
    return Response(service.to_xlsx(t, prm), media_type=XLSX,
                    headers={"Content-Disposition": f'attachment; filename="gazyar-{key}-{stamp}.xlsx"'})


@router.post("/{key}/snapshots", response_model=SnapshotOut, status_code=201)
def snapshot(key: str, body: SnapshotIn, request: Request, db: DB, staff: StaffCtx = require(P.REPORTS_EXPORT)) -> SnapshotOut:
    prm = service.Params(body.region_id, body.date_from, body.date_to, body.tier, body.expert_id)
    t = service.run(db, key, prm)
    version = int(db.scalar(select(func.coalesce(func.max(ReportSnapshot.version), 0)).where(ReportSnapshot.report_key == key)) or 0) + 1
    x = files.save_document(db, service.to_xlsx(t, prm), purpose="report", owner_type="staff", owner_id=staff.id,
                            original_name=f"{key}-v{version}.xlsx", mime=XLSX, max_bytes=50 * 1024 * 1024)
    c = files.save_document(db, service.to_csv(t), purpose="report", owner_type="staff", owner_id=staff.id,
                            original_name=f"{key}-v{version}.csv", mime="text/csv", max_bytes=50 * 1024 * 1024)
    s = ReportSnapshot(report_key=key, version=version, title=t.title, params=body.model_dump(mode="json", exclude={"note"}),
                       summary=t.summary, row_count=len(t.rows), xlsx_file_id=x.id, csv_file_id=c.id, created_by=staff.id,
                       note=body.note)
    db.add(s)
    db.flush()
    audit.record(db, staff.actor, "report.snapshot", "report", key, None, {"version": version}, request)
    return _snap_out(s)
