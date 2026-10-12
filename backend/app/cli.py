"""Operational commands: python -m app.cli <command>

  init-db            create tables (dev/test; production uses `alembic upgrade head`)
  seed [--demo]      settings, points rules, regions, an admin account; --demo adds sample data
  create-admin       interactive-free admin creation: --username --password --name
  release-points     move due pending points to available (cron: daily)
  drain-sms          send queued SMS (cron: every minute when the scheduler is off)
"""

from __future__ import annotations

import argparse
import random
import sys

from sqlalchemy import select

from app import models  # noqa: F401
from app.core import clock, crypto, jalali
from app.core.db import Base, SessionLocal, engine


def init_db() -> None:
    Base.metadata.create_all(engine())


def _ensure_regions(db) -> dict[str, int]:
    from app.modules.regions.models import Region

    out = {}
    root = db.scalar(select(Region).where(Region.code == "R2"))
    if root is None:
        root = Region(name="منطقهٔ ۲ گاز رشت", code="R2")
        db.add(root)
        db.flush()
    out["R2"] = root.id
    for i, name in enumerate(["ناحیهٔ گلسار", "ناحیهٔ منظریه", "ناحیهٔ بلوار شهید انصاری", "ناحیهٔ معلم", "ناحیهٔ لاکانی"], 1):
        code = f"R2-Z{i}"
        z = db.scalar(select(Region).where(Region.code == code))
        if z is None:
            z = Region(name=name, code=code, parent_id=root.id)
            db.add(z)
            db.flush()
        out[code] = z.id
    return out


def create_admin(db, username: str, password: str, name: str, roles: list[str] | None = None,
                 must_change: bool = True, regions: list[int] | None = None):
    from app.core import security
    from app.modules.staff.models import StaffUser

    st = db.scalar(select(StaffUser).where(StaffUser.username == username))
    if st is None:
        st = StaffUser(username=username, full_name=name, password_hash=security.hash_password(password),
                       roles=roles or ["super_admin"], must_change_password=must_change,
                       service_region_ids=regions or [])
        db.add(st)
        db.flush()
    return st


SEASON = [0.55, 0.25, 0.12, 0.08, 0.08, 0.09, 0.15, 0.45, 0.95, 1.30, 1.25, 1.00]  # Jalali month factors (Farvardin..Esfand)


def seed(demo: bool) -> None:
    from app.modules.points.service import seed_rules

    init_db()
    db = SessionLocal()
    try:
        seed_rules(db)
        regions = _ensure_regions(db)
        create_admin(db, "admin", "Gazyar1405", "مدیر سامانه", must_change=not demo)
        if demo:
            _demo(db, regions)
        db.commit()
    finally:
        db.close()


def _demo(db, regions: dict[str, int]) -> None:
    from app.modules.subscribers import service as subs
    from app.modules.subscribers.models import ConsumptionHistory, Subscriber

    rnd = random.Random(1405)
    zones = [v for k, v in regions.items() if k != "R2"]
    create_admin(db, "operator", "Gazyar1405", "اپراتور نمونه", ["operator"], False)
    create_admin(db, "technician", "Gazyar1405", "کارشناس فنی نمونه", ["technician"], False)
    create_admin(db, "ambassador1", "Gazyar1405", "سفیر ناحیهٔ گلسار", ["ambassador"], False, [zones[0], zones[1]])
    create_admin(db, "ambassador2", "Gazyar1405", "سفیر ناحیهٔ معلم", ["ambassador"], False, [zones[2], zones[3], zones[4]])
    create_admin(db, "finance", "Gazyar1405", "واحد مالی نمونه", ["finance"], False)
    if db.scalar(select(Subscriber.id).limit(1)):
        return
    first = ["علی", "مریم", "رضا", "زهرا", "حسین", "فاطمه", "محمد", "نرگس", "مهدی", "سارا"]
    last = ["رحیمی", "کاظمی", "حسینی", "محمدی", "نوروزی", "صادقی", "قاسمی", "اکبری", "رضایی", "عباسی"]
    this_year = jalali.jdate_of(clock.now()).year
    for i in range(300):
        sn = f"{4000000000 + i * 37:d}"
        mobile = f"0912{1000000 + i:07d}"
        scale = rnd.choice([2200, 3200, 3800, 4500, 5200, 6500, 8000])  # some below the 3500 threshold
        s = Subscriber(subscription_no=sn, mobile_enc=crypto.encrypt(mobile), mobile_bidx=subs.mobile_bidx(mobile),
                       full_name=f"{rnd.choice(first)} {rnd.choice(last)}", region_id=rnd.choice(zones),
                       address="رشت", meter_serial=f"MTR-{i:05d}")
        db.add(s)
        db.flush()
        for y in range(this_year - 3, this_year):
            yearly = scale * rnd.uniform(0.9, 1.1)
            for m in range(1, 13):
                db.add(ConsumptionHistory(subscriber_id=s.id, jyear=y, jmonth=m,
                                          volume_m3=round(yearly * SEASON[m - 1] / sum(SEASON) * rnd.uniform(0.9, 1.1), 1)))
    db.flush()
    subs.refresh_baselines(db)
    print("demo data: 300 subscribers (mobiles 09121000000…09121000299, subscription 4000000000 + 37·i)")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="app.cli")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("init-db")
    s = sub.add_parser("seed")
    s.add_argument("--demo", action="store_true")
    c = sub.add_parser("create-admin")
    c.add_argument("--username", required=True)
    c.add_argument("--password", required=True)
    c.add_argument("--name", default="مدیر سامانه")
    sub.add_parser("release-points")
    sub.add_parser("drain-sms")
    a = ap.parse_args(argv)
    if a.cmd == "init-db":
        init_db()
    elif a.cmd == "seed":
        seed(a.demo)
    elif a.cmd == "create-admin":
        db = SessionLocal()
        create_admin(db, a.username.lower(), a.password, a.name)
        db.commit()
        db.close()
    else:
        db = SessionLocal()
        if a.cmd == "release-points":
            from app.modules.points.service import release_due

            print("released", release_due(db))
        else:
            from app.core.sms import drain

            print("sent", drain(db))
        db.commit()
        db.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())

