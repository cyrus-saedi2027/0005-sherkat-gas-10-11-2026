from __future__ import annotations

from fastapi import APIRouter, Depends

from app.core.deps import DB, CurrentStaff
from app.core.pagination import PageParams, page_params
from app.modules.notifications import service
from app.modules.notifications.schemas import MarkRead, NotificationOut, NotificationPage

router = APIRouter(prefix="/notifications", tags=["admin:notifications"])


@router.get("", response_model=NotificationPage)
def my_notifications(staff: CurrentStaff, db: DB, p: PageParams = Depends(page_params), unread: bool = False):
    rows, total, n_unread = service.list_for(db, "staff", staff.id, p.size, p.offset, unread)
    return NotificationPage(items=[NotificationOut.model_validate(r, from_attributes=True) for r in rows],
                            total=total, unread=n_unread, page=p.page, size=p.size)


@router.post("/read")
def mark_read(body: MarkRead, staff: CurrentStaff, db: DB) -> dict[str, int]:
    return {"updated": service.mark_read(db, "staff", staff.id, body.ids)}
