from __future__ import annotations

from typing import Any

from sqlalchemy import JSON, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base, Timestamped


class ReportSnapshot(Timestamped, Base):
    """A frozen, versioned report output (R31: reports must be recordable as versions)."""

    __tablename__ = "report_snapshots"
    report_key: Mapped[str] = mapped_column(String(40), index=True)
    version: Mapped[int]
    title: Mapped[str] = mapped_column(String(200))
    params: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    summary: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    row_count: Mapped[int]
    xlsx_file_id: Mapped[str] = mapped_column(String(32))
    csv_file_id: Mapped[str] = mapped_column(String(32))
    created_by: Mapped[int]
    note: Mapped[str | None] = mapped_column(String(300))
