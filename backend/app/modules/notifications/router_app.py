from __future__ import annotations

from fastapi import APIRouter, Depends

from app.core.deps import DB, CurrentUser
from app.core.pagination import PageParams, page_params
from app.modules.notifications import service
from app.modules.notifications.schemas import MarkRead, NotificationOut, NotificationPage

router = APIRouter(prefix="/notifications", tags=["app:notifications"])


@router.get("", response_model=NotificationPage)
def my_notifications(user: CurrentUser, db: DB, p: PageParams = Depends(page_params), unread: bool = False):
    rows, total, n_unread = service.list_for(db, "user", user.id, p.size, p.offset, unread)
    return NotificationPage(items=[NotificationOut.model_validate(r, from_attributes=True) for r in rows],
                            total=total, unread=n_unread, page=p.page, size=p.size)


@router.post("/read")
def mark_read(body: MarkRead, user: CurrentUser, db: DB) -> dict[str, int]:
    return {"updated": service.mark_read(db, "user", user.id, body.ids)}
