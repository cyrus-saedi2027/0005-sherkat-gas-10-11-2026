from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import select

from app.core import clock, jalali
from app.core import settings_registry as reg
from app.core.deps import DB, CurrentUser
from app.core.pagination import PageParams, page_params, paginate
from app.modules.points import service
from app.modules.points.models import PointsLedger
from app.modules.points.schemas import BalanceOut, LedgerOut, LedgerPage

router = APIRouter(prefix="/points", tags=["app:points"])


def ledger_out(db, e: PointsLedger) -> LedgerOut:
    return LedgerOut(id=e.id, event_type=e.event_type, event_title=service.event_title(db, e.event_type),
                     amount=e.amount, status=e.status, reason=e.reason, ref_type=e.ref_type, ref_id=e.ref_id,
                     period_key=e.period_key, available_at=e.available_at, created_at=e.created_at,
                     suspended_reason=e.suspended_reason)


@router.get("/balance", response_model=BalanceOut)
def my_balance(user: CurrentUser, db: DB) -> BalanceOut:
    b = service.balance(db, user.id)
    rate = reg.get_int(db, "finance.point_rial_rate")
    return BalanceOut(available=b.available, pending=b.pending, suspended=b.suspended, total=b.total,
                      rial_rate=rate, available_rial=b.available * rate,
                      next_release_at=jalali.next_month_start_utc(clock.now()) if b.pending else None)


@router.get("/ledger", response_model=LedgerPage)
def my_ledger(user: CurrentUser, db: DB, p: PageParams = Depends(page_params)) -> LedgerPage:
    stmt = select(PointsLedger).where(PointsLedger.user_id == user.id).order_by(PointsLedger.id.desc())
    rows, total = paginate(db, stmt, p)
    return LedgerPage(items=[ledger_out(db, e) for e in rows], total=total, page=p.page, size=p.size)
