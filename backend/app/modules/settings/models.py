from __future__ import annotations

from typing import Any

from sqlalchemy import JSON, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base, Timestamped


class Setting(Timestamped, Base):
    __tablename__ = "settings"
    key: Mapped[str] = mapped_column(String(64), unique=True)
    value: Mapped[Any] = mapped_column(JSON)
    updated_by: Mapped[int | None]
