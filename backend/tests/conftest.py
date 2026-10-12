"""Test harness. Runs on SQLite by default; set GAZYAR_TEST_DATABASE_URL to run on PostgreSQL."""

from __future__ import annotations

import io
import os
import tempfile
from collections.abc import Iterator
from datetime import UTC, datetime
from pathlib import Path

_tmp = Path(tempfile.mkdtemp(prefix="gazyar-test-"))
os.environ["GAZYAR_ENV"] = "test"
os.environ["GAZYAR_DATABASE_URL"] = os.environ.get("GAZYAR_TEST_DATABASE_URL", f"sqlite:///{_tmp / 'test.db'}")
os.environ["GAZYAR_UPLOAD_DIR"] = str(_tmp / "uploads")
os.environ["GAZYAR_EXPOSE_DEV_OTP"] = "true"

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from PIL import Image  # noqa: E402
from sqlalchemy import text  # noqa: E402
from sqlalchemy.orm import Session  # noqa: E402

from app import models  # noqa: E402,F401
from app.core import clock, crypto, ratelimit, security, sms  # noqa: E402
from app.core.db import Base, SessionLocal, configure, engine  # noqa: E402
from app.main import app  # noqa: E402

NOW = datetime(2026, 10, 12, 8, 30, tzinfo=UTC)  # = 1405-07-20 12:00 Tehran
PASSWORD = "Passw0rd-123"

configure(os.environ["GAZYAR_DATABASE_URL"])
Base.metadata.drop_all(engine())
Base.metadata.create_all(engine())


def _wipe() -> None:
    with engine().begin() as conn:
        if conn.dialect.name == "postgresql":
            names = ", ".join(f'"{t.name}"' for t in Base.metadata.sorted_tables)
            conn.execute(text(f"TRUNCATE {names} RESTART IDENTITY CASCADE"))
        else:
            for t in reversed(Base.metadata.sorted_tables):
                conn.execute(t.delete())


@pytest.fixture(autouse=True)
def _clean() -> Iterator[None]:
    _wipe()
    ratelimit.reset()
    sms.DEV_LAST.clear()
    clock.freeze(NOW)
    yield
    clock.freeze(None)


@pytest.fixture
def db() -> Iterator[Session]:
    s = SessionLocal()
    try:
        yield s
        s.commit()
    finally:
        s.close()


@pytest.fixture
def client() -> TestClient:
    return TestClient(app, raise_server_exceptions=True)


# ───────────── factories ─────────────

def make_region(db: Session, code: str = "R2", name: str = "منطقه ۲", parent_id: int | None = None):
    from app.modules.regions.models import Region

    r = Region(name=name, code=code, parent_id=parent_id)
    db.add(r)
    db.flush()
    return r


def make_subscriber(db: Session, *, sn: str = "1234567890", mobile: str = "09121112233", annual: float = 6000,
                    region_id: int | None = None, years: tuple[int, ...] = (1402, 1403, 1404), active: bool = True):
    from app.modules.subscribers import service as subs
    from app.modules.subscribers.models import ConsumptionHistory, Subscriber

    s = Subscriber(subscription_no=sn, mobile_enc=crypto.encrypt(mobile), mobile_bidx=subs.mobile_bidx(mobile),
                   full_name="مشترک آزمایشی", region_id=region_id, is_active=active)
    db.add(s)
    db.flush()
    for y in years:
        for m in range(1, 13):
            db.add(ConsumptionHistory(subscriber_id=s.id, jyear=y, jmonth=m, volume_m3=annual / 12))
    db.flush()
    subs.refresh_baselines(db, [s.id])
    return s


def make_user(db: Session, subscriber=None, **kw):
    from app.modules.users.models import User

    subscriber = subscriber or make_subscriber(db, **kw)
    mobile = crypto.decrypt(subscriber.mobile_enc)
    u = User(subscriber_id=subscriber.id, mobile_enc=crypto.encrypt(mobile),
             mobile_bidx=crypto.blind_index(mobile, purpose="mobile"), referral_code=f"R{subscriber.id:06d}",
             terms_accepted_at=NOW, privacy_accepted_at=NOW, terms_version="1", first_name="علی", last_name="رضایی")
    db.add(u)
    db.flush()
    return u


def make_staff(db: Session, role: str = "super_admin", username: str | None = None, **kw):
    from app.modules.staff.models import StaffUser

    st = StaffUser(username=username or f"{role}_{os.urandom(3).hex()}", full_name=f"کاربر {role}",
                   password_hash=security.hash_password(PASSWORD), roles=[role], **kw)
    db.add(st)
    db.flush()
    return st


def staff_headers(st) -> dict[str, str]:
    return {"Authorization": f"Bearer {security.issue_access_token('staff', st.id)}"}


def user_headers(u) -> dict[str, str]:
    return {"Authorization": f"Bearer {security.issue_access_token('user', u.id)}"}


def jpeg_bytes(color: tuple[int, int, int] = (200, 30, 30), size: tuple[int, int] = (64, 48)) -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", size, color).save(buf, "JPEG")
    return buf.getvalue()
