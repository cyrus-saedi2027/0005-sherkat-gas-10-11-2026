"""Signed file delivery. Access was checked when the URL was minted; the signature proves it."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Query
from fastapi.responses import FileResponse

from app.core import storage
from app.core.deps import DB
from app.core.errors import AppError
from app.modules.files.service import get

router = APIRouter(prefix="/files", tags=["files"])


@router.get("/{file_id}", response_class=FileResponse)
def download(file_id: str, db: DB, v: Annotated[str, Query(pattern="^(full|thumb)$")] = "full",
             exp: Annotated[int, Query()] = 0, sig: Annotated[str, Query(max_length=64)] = "") -> FileResponse:
    if not storage.verify(file_id, v, exp, sig):
        raise AppError("bad_signature", "لینک فایل نامعتبر یا منقضی است.", 403)
    f = get(db, file_id)
    if f is None:
        raise AppError("not_found", "فایل پیدا نشد.", 404)
    key = f.thumb_key if v == "thumb" and f.thumb_key else f.storage_key
    try:
        path = storage.path_of(key)
    except FileNotFoundError as e:
        raise AppError("not_found", "فایل پیدا نشد.", 404) from e
    is_image = f.mime.startswith("image/")
    return FileResponse(
        path,
        media_type=f.mime,
        headers={
            "Cache-Control": "private, max-age=600",
            "X-Content-Type-Options": "nosniff",
            # Non-images are always downloaded, never rendered in our origin.
            "Content-Disposition": "inline" if is_image else f'attachment; filename="{file_id}"',
        },
    )

