from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import JSON, Float, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base, Timestamped


class Subscriber(Timestamped, Base):
    """The authorised subscriber list imported from the gas company's Excel (R01, R07)."""

    __tablename__ = "subscribers"
    subscription_no: Mapped[str] = mapped_column(String(24), unique=True)
    mobile_enc: Mapped[str | None] = mapped_column(String(512))
    mobile_bidx: Mapped[str | None] = mapped_column(String(64), index=True)
    full_name: Mapped[str | None] = mapped_column(String(160))
    address: Mapped[str | None] = mapped_column(String(500))
    region_id: Mapped[int | None] = mapped_column(ForeignKey("regions.id"), index=True)
    meter_serial: Mapped[str | None] = mapped_column(String(40))
    is_active: Mapped[bool] = mapped_column(default=True, index=True)
    import_batch_id: Mapped[int | None] = mapped_column(ForeignKey("import_batches.id"))
    # Cached annual baseline (mean of yearly sums over the baseline years); refreshed on import.
    baseline_annual_m3: Mapped[float | None] = mapped_column(Float)


class ConsumptionHistory(Timestamped, Base):
    """Historical monthly consumption (same-period comparison over 3 years, R04)."""

    __tablename__ = "consumption_history"
    __table_args__ = (UniqueConstraint("subscriber_id", "jyear", "jmonth"),)
    subscriber_id: Mapped[int] = mapped_column(ForeignKey("subscribers.id", ondelete="CASCADE"), index=True)
    jyear: Mapped[int]
    jmonth: Mapped[int]
    volume_m3: Mapped[float] = mapped_column(Float)
    import_batch_id: Mapped[int | None] = mapped_column(ForeignKey("import_batches.id"))


class ImportBatch(Timestamped, Base):
    __tablename__ = "import_batches"
    kind: Mapped[str] = mapped_column(String(16))  # subscribers | consumption | combined
    filename: Mapped[str] = mapped_column(String(255))
    file_id: Mapped[str | None] = mapped_column(String(32))
    uploaded_by: Mapped[int | None]
    status: Mapped[str] = mapped_column(String(16), default="validated")  # validated | committed | failed
    row_count: Mapped[int] = mapped_column(default=0)
    error_count: Mapped[int] = mapped_column(default=0)
    errors: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list)
    summary: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    committed_at: Mapped[datetime | None]
