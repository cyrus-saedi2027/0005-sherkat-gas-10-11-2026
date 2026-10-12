"""Background jobs (single process). In multi-worker deployments run them via `python -m app.cli` + cron instead."""

from __future__ import annotations

import logging

from apscheduler.schedulers.background import BackgroundScheduler

from app.core.db import SessionLocal

log = logging.getLogger("gazyar.scheduler")
_sched: BackgroundScheduler | None = None


def _job(fn) -> None:
    db = SessionLocal()
    try:
        fn(db)
        db.commit()
    except Exception:
        db.rollback()
        log.exception("job %s failed", getattr(fn, "__name__", fn))
    finally:
        db.close()


def drain_sms(db) -> None:
    from app.core import sms

    sms.drain(db)


def release_points(db) -> None:
    from app.modules.points.service import release_due

    release_due(db)


def start() -> None:
    global _sched
    if _sched is not None:
        return
    _sched = BackgroundScheduler(timezone="Asia/Tehran")
    _sched.add_job(lambda: _job(drain_sms), "interval", seconds=5, id="sms", max_instances=1, coalesce=True)
    _sched.add_job(lambda: _job(release_points), "cron", hour="0,6,12,18", minute=5, id="points", coalesce=True)
    _sched.start()
