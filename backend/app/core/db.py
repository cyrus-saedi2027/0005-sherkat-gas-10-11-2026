"""Database engine, session factory and declarative base."""

from __future__ import annotations

from collections.abc import Iterator
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import DateTime, MetaData, create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, sessionmaker
from sqlalchemy.types import TypeDecorator

from app.core import clock
from app.core.config import get_settings

# Deterministic constraint names → Alembic diffs stay stable across SQLite/PostgreSQL.
NAMING = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_N_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class UTCDateTime(TypeDecorator[datetime]):
    """Always hands out tz-aware UTC datetimes.

    SQLite drops tzinfo, which made `aware < naive` comparisons explode only in
    tests and never on PostgreSQL — the classic "works in prod, fails in CI"
    split. Normalising at the type boundary removes the whole class of bug.
    """

    impl = DateTime(timezone=True)
    cache_ok = True

    def process_bind_param(self, value: datetime | None, dialect: Any) -> datetime | None:
        if value is None:
            return None
        if value.tzinfo is None:
            raise ValueError("naive datetime passed to UTCDateTime column")
        value = value.astimezone(UTC)
        return value.replace(tzinfo=None) if dialect.name == "sqlite" else value

    def process_result_value(self, value: datetime | None, dialect: Any) -> datetime | None:
        if value is None:
            return None
        return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)


class Base(DeclarativeBase):
    metadata = MetaData(naming_convention=NAMING)
    type_annotation_map = {datetime: UTCDateTime()}


class Timestamped:
    """id + created_at + updated_at for every table (ARCHITECTURE §3)."""

    id: Mapped[int] = mapped_column(primary_key=True)
    created_at: Mapped[datetime] = mapped_column(default=lambda: clock.now(), index=True)
    updated_at: Mapped[datetime] = mapped_column(default=lambda: clock.now(), onupdate=lambda: clock.now())


def _make_engine(url: str) -> Engine:
    kwargs: dict[str, Any] = {"echo": get_settings().sql_echo, "future": True}
    if url.startswith("sqlite"):
        kwargs["connect_args"] = {"check_same_thread": False}
    else:
        kwargs.update(pool_pre_ping=True, pool_size=10, max_overflow=20)
    eng = create_engine(url, **kwargs)
    if url.startswith("sqlite"):

        @event.listens_for(eng, "connect")
        def _sqlite_pragmas(dbapi_conn: Any, _rec: Any) -> None:
            # pysqlite's own transaction handling breaks SAVEPOINT (used for
            # race-safe idempotent awards); take over BEGIN ourselves — the
            # documented SQLAlchemy recipe.
            dbapi_conn.isolation_level = None
            cur = dbapi_conn.cursor()
            cur.execute("PRAGMA foreign_keys=ON")
            cur.execute("PRAGMA journal_mode=WAL")
            cur.execute("PRAGMA busy_timeout=5000")
            cur.close()

        @event.listens_for(eng, "begin")
        def _sqlite_begin(conn: Any) -> None:
            conn.exec_driver_sql("BEGIN")

    return eng


_engine: Engine | None = None
_SessionLocal: sessionmaker[Session] | None = None


def configure(url: str | None = None) -> Engine:
    """(Re)bind the engine. Tests call this with their own URL."""
    global _engine, _SessionLocal
    if _engine is not None:
        _engine.dispose()
    url = url or get_settings().database_url
    if url.startswith("sqlite:///"):
        from pathlib import Path

        Path(url.removeprefix("sqlite:///")).parent.mkdir(parents=True, exist_ok=True)
    _engine = _make_engine(url)
    _SessionLocal = sessionmaker(bind=_engine, autoflush=False, expire_on_commit=False)
    return _engine


def engine() -> Engine:
    if _engine is None:
        configure()
    assert _engine is not None
    return _engine


def SessionLocal() -> Session:  # noqa: N802 — reads like the conventional factory name
    if _SessionLocal is None:
        configure()
    assert _SessionLocal is not None
    return _SessionLocal()


def get_db() -> Iterator[Session]:
    """Request-scoped session; commit on success, rollback on any exception."""
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
