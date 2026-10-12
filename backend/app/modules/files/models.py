from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from app.core import clock
from app.core.db import Base


class StoredFile(Base):
    __tablename__ = "files"
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=lambda: uuid.uuid4().hex)
    owner_type: Mapped[str] = mapped_column(String(8), index=True)  # user | staff | system
    owner_id: Mapped[int | None] = mapped_column(index=True)
    purpose: Mapped[str] = mapped_column(String(24), index=True)
    original_name: Mapped[str | None] = mapped_column(String(255))
    mime: Mapped[str] = mapped_column(String(128))
    size: Mapped[int]
    sha256: Mapped[str] = mapped_column(String(64), index=True)
    width: Mapped[int | None]
    height: Mapped[int | None]
    exif_taken_at: Mapped[datetime | None]
    storage_key: Mapped[str] = mapped_column(String(255))
    thumb_key: Mapped[str | None] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(default=lambda: clock.now(), index=True)
