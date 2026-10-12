from __future__ import annotations

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base, Timestamped


class Region(Timestamped, Base):
    """Region → zone hierarchy (e.g. «منطقهٔ ۲ رشت» → ناحیه‌ها). R01, R27 filters, R38 assignment."""

    __tablename__ = "regions"
    name: Mapped[str] = mapped_column(String(120))
    code: Mapped[str] = mapped_column(String(32), unique=True)
    parent_id: Mapped[int | None] = mapped_column(ForeignKey("regions.id"), index=True)
    is_active: Mapped[bool] = mapped_column(default=True)
