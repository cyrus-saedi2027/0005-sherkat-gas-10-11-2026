from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core import clock, images, ratelimit, storage
from app.core import settings_registry as reg
from app.core.errors import AppError
from app.modules.files.models import StoredFile

IMAGE_PURPOSES = {"meter_photo", "case_before", "case_after", "ticket_attachment", "content_cover", "reward_image"}


def save_image(db: Session, raw: bytes, *, purpose: str, owner_type: str, owner_id: int | None,
               original_name: str | None = None) -> StoredFile:
    if purpose not in IMAGE_PURPOSES:
        raise AppError("bad_purpose", "نوع فایل معتبر نیست.", 422)
    if owner_type == "user" and owner_id is not None:
        ratelimit.enforce(f"upload:user:{owner_id}", reg.get_int(db, "uploads.daily_per_user"), 86_400,
                          "سقف ارسال تصویر امروز پر شده است؛ فردا دوباره تلاش کنید.")
    max_bytes = reg.get_int(db, "uploads.max_mb") * 1024 * 1024
    img = images.process_image(raw, max_bytes)
    fid = uuid.uuid4().hex
    day = clock.now().strftime("%Y/%m")
    key, tkey = f"{purpose}/{day}/{fid}.webp", f"{purpose}/{day}/{fid}.thumb.webp"
    storage.save(key, img.data)
    storage.save(tkey, img.thumb)
    row = StoredFile(id=fid, owner_type=owner_type, owner_id=owner_id, purpose=purpose,
                     original_name=(original_name or "")[:255] or None, mime=img.mime, size=len(img.data),
                     sha256=img.sha256, width=img.width, height=img.height, exif_taken_at=img.exif_taken_at,
                     storage_key=key, thumb_key=tkey)
    db.add(row)
    db.flush()
    return row


def save_document(db: Session, raw: bytes, *, purpose: str, owner_type: str, owner_id: int | None,
                  original_name: str, mime: str, max_bytes: int) -> StoredFile:
    """Non-image files (Excel imports, PDF attachments). Content is never executed or served inline."""
    import hashlib

    if len(raw) > max_bytes:
        raise AppError("file_too_large", "حجم فایل بیش از حد مجاز است.", 413)
    fid = uuid.uuid4().hex
    ext = (original_name.rsplit(".", 1)[-1] if "." in original_name else "bin").lower()[:8]
    key = f"{purpose}/{clock.now().strftime('%Y/%m')}/{fid}.{ext}"
    storage.save(key, raw)
    row = StoredFile(id=fid, owner_type=owner_type, owner_id=owner_id, purpose=purpose,
                     original_name=original_name[:255], mime=mime, size=len(raw),
                     sha256=hashlib.sha256(raw).hexdigest(), storage_key=key)
    db.add(row)
    db.flush()
    return row


def get(db: Session, file_id: str) -> StoredFile | None:
    return db.get(StoredFile, file_id)


def find_by_sha(db: Session, sha: str, exclude_id: str | None = None) -> list[StoredFile]:
    stmt = select(StoredFile).where(StoredFile.sha256 == sha)
    if exclude_id:
        stmt = stmt.where(StoredFile.id != exclude_id)
    return list(db.scalars(stmt).all())


def url(file_id: str | None, variant: str = "full") -> str | None:
    return storage.signed_url(file_id, variant)
