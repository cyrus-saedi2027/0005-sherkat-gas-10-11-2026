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
            _demo_rich(db)
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




def _demo_rich(db) -> None:
    """Store, content, survey and journeys at every stage — for the client demo and E2E tests."""
    from datetime import timedelta

    from app.core import security
    from app.modules.cases.models import Case, CaseCall, CaseChecklist, CaseEstimate
    from app.modules.content.models import Article
    from app.modules.points import service as points
    from app.modules.readings.models import MeterReading
    from app.modules.store import service as store
    from app.modules.store.models import RewardCategory, RewardItem
    from app.modules.subscribers.models import Subscriber
    from app.modules.surveys.models import Survey, SurveyQuestion
    from app.modules.users.models import User

    if db.scalar(select(RewardItem.id).limit(1)):
        return
    store.seed_categories(db)
    cats = {c.key: c.id for c in db.scalars(select(RewardCategory)).all()}
    items = [
        ("cash", "برداشت نقدی به حساب بانکی", "cash", 500, 0, None, None),
        ("pet_food", "بستهٔ غذای خشک گربه (۲ کیلوگرم)", "product", 900, 0, 40, None),
        ("pet_food", "بستهٔ غذای سگ (۳ کیلوگرم)", "product", 1100, 0, 25, None),
        ("insulation", "بستهٔ نوار درزگیر پنجره و در", "product", 350, 0, 200, None),
        ("insulation", "پوشش عایق لوله و آبگرمکن", "product", 600, 0, 80, None),
        ("insulation", "شیر ترموستاتیک رادیاتور", "product", 1500, 0, 60, None),
        ("repair_discount", "۳۰٪ تخفیف سرویس بخاری و دودکش", "discount", 400, 0, None, None),
        ("repair_discount", "۲۰٪ تخفیف سرویس پکیج و آبگرمکن", "discount", 700, 0, None, None),
        ("charity", "کمک به خیریهٔ کهریزک", "donation", 100, 0, None, "آسایشگاه کهریزک"),
        ("charity", "کمک به محک", "donation", 100, 0, None, "مؤسسهٔ محک"),
        ("stationery", "بستهٔ لوازم‌التحریر دانش‌آموزی", "product", 450, 0, 150, None),
        ("gift", "کارت هدیهٔ خرید ۵۰۰ هزار ریالی", "product", 550, 500_000, 100, None),
    ]
    for i, (cat, title, kind, cost, rial, stock, charity) in enumerate(items):
        db.add(RewardItem(category_id=cats[cat], title=title, kind=kind, points_cost=cost, rial_value=rial, stock=stock,
                          charity_name=charity, needs_address=kind == "product", sort=i,
                          description="از محل امتیازهای صرفه‌جویی شما در طرح گازیار."))
    articles = [
        ("ده راهکار ساده برای کاهش مصرف گاز", "tip", [], "دمای خانه را روی ۱۸ تا ۲۱ درجه نگه دارید؛ هر یک درجه کاهش حدود ۶ درصد صرفه‌جویی دارد."),
        ("چرا درزگیری پنجره‌ها مهم است؟", "article", ["low_cost", "no_cost"], "بخش بزرگی از گرمای خانه از درز پنجره‌ها هدر می‌رود. نوار درزگیر ارزان و نصبش ساده است."),
        ("نشانه‌های بخاری فرسوده و خطرناک", "guide", ["high_cost"], "شعلهٔ زرد، دوده و بوی گاز نشانهٔ سوختن ناقص است؛ خطر گازگرفتگی را جدی بگیرید."),
        ("آبگرمکن را درست تنظیم کنید", "tip", [], "دمای ۵۰ تا ۵۵ درجه برای مصرف خانگی کافی است و مصرف گاز را کم می‌کند."),
        ("عایق‌کاری سقف و دیوار؛ سرمایه‌ای که برمی‌گردد", "article", ["high_cost", "low_cost"], "عایق‌کاری مناسب تا ۳۰ درصد هزینهٔ گرمایش را کم می‌کند."),
        ("طرح گازیار چطور کار می‌کند؟", "news", [], "قرائت ماهانهٔ کنتور، مقایسه با میانگین سه سال قبل و دریافت امتیاز برای هر درصد کاهش."),
    ]
    for i, (title, cat, tiers, body) in enumerate(articles):
        db.add(Article(slug=f"demo-{i + 1}", title=title, summary=body[:120], body=body + "\n\n" + body, category=cat,
                       target_tiers=tiers, status="published", published_at=clock.now() - timedelta(days=i)))
    s = Survey(title="نظرسنجی رضایت از طرح گازیار", description="نظر شما به بهبود طرح کمک می‌کند.", status="active")
    db.add(s)
    db.flush()
    for i, (kind, text, opts) in enumerate([("rating", "چقدر از طرح گازیار راضی هستید؟", []),
                                            ("single", "از کجا با طرح آشنا شدید؟", ["پیامک", "دوستان و آشنایان", "سفیر طرح", "شبکه‌های اجتماعی"]),
                                            ("text", "پیشنهاد شما برای بهتر شدن طرح چیست؟", [])]):
        db.add(SurveyQuestion(survey_id=s.id, kind=kind, text=text, options=opts, required=kind != "text", sort=i))

    # Journeys: registered users with readings in every review state, and cases at several stages.
    subs = [x for x in db.scalars(select(Subscriber).order_by(Subscriber.id)).all() if (x.baseline_annual_m3 or 0) >= 3500][:24]
    today = jalali.to_tehran(clock.now()).date()
    period = jalali.period_key(clock.now())
    prev_period = jalali.shift_period(period, -1)
    from app.modules.staff.models import StaffUser

    amb = db.scalar(select(StaffUser).where(StaffUser.username == "ambassador1"))
    statuses = ["pending", "pending", "pending", "flagged", "needs_correction", "approved", "approved", "rejected"]
    for i, sub in enumerate(subs):
        mobile = crypto.decrypt(sub.mobile_enc) or ""
        u = User(subscriber_id=sub.id, mobile_enc=crypto.encrypt(mobile) or "", mobile_bidx=sub.mobile_bidx or "",
                 first_name=sub.full_name.split(" ")[0] if sub.full_name else None,
                 last_name=" ".join(sub.full_name.split(" ")[1:]) if sub.full_name else None,
                 password_hash=security.hash_password("Gazyar1405") if i == 0 else None,
                 login_method="password" if i == 0 else "otp", terms_version="1", terms_accepted_at=clock.now(),
                 privacy_accepted_at=clock.now(), referral_code=f"DEMO{i:03d}")
        db.add(u)
        db.flush()
        points.award(db, user_id=u.id, event_type="signup", idempotency_key=f"signup:subscriber:{sub.id}", ref_type="user", ref_id=u.id)
        base = round((sub.baseline_annual_m3 or 4000) * 2.4)
        db.add(MeterReading(user_id=u.id, subscriber_id=sub.id, period_key=prev_period, declared_value=base, approved_value=base,
                            reading_date=today - timedelta(days=30), status="approved", reviewed_at=clock.now() - timedelta(days=25)))
        st = statuses[i % len(statuses)]
        monthly = (sub.baseline_annual_m3 or 4000) / 12
        val = round(base + monthly * (0.75 if i % 3 else 1.05) * (0.2 if st == "flagged" else 1))
        db.add(MeterReading(user_id=u.id, subscriber_id=sub.id, period_key=period, declared_value=val,
                            approved_value=val if st == "approved" else None, reading_date=today - timedelta(days=i % 5),
                            status=st, flags=["sudden_drop"] if st == "flagged" else [],
                            reason_code="blurry_photo" if st in ("needs_correction", "rejected") else None,
                            reviewed_at=clock.now() if st not in ("pending", "flagged") else None))
        if i < 8 and amb is not None:
            stage = ["assigned", "contacted", "evaluated", "visit_scheduled", "awaiting_consent", "pending_final_approval", "completed", "new"][i]
            c = Case(user_id=u.id, subscriber_id=sub.id, region_id=sub.region_id, status=stage,
                     ambassador_id=None if stage == "new" else amb.id, assignment_method="auto", assigned_at=clock.now(),
                     tier="high_cost" if i in (4, 5) else ("low_cost" if i in (2, 3, 6) else None),
                     needs_field_visit=i in (3, 4, 5))
            db.add(c)
            db.flush()
            if stage not in ("new", "assigned"):
                db.add(CaseCall(case_id=c.id, staff_id=amb.id, called_at=clock.now(), outcome="reached", note="هماهنگ شد"))
                db.add(CaseChecklist(case_id=c.id, floor_area_m2=120 + i * 10, residents_count=3 + i % 3, insulation="partial",
                                     window_seals="poor", chimney_status="ok",
                                     heating_equipment=[{"type": "heater", "count": 2, "condition": "fair", "age_years": 9}]))
            if stage == "awaiting_consent":
                db.add(CaseEstimate(case_id=c.id, items=[{"title": "تعویض بخاری", "qty": 1, "unit_cost_rial": 60_000_000}],
                                    total_cost_rial=60_000_000, free_cap_rial=5_000_000, subscriber_share_pct=30,
                                    subscriber_share_rial=18_000_000, program_share_rial=42_000_000, status="sent"))
            u.tier = c.tier
    db.flush()
    print("rich demo: store items, articles, survey, 24 users with readings, 8 cases (user 1 password: Gazyar1405)")


if __name__ == "__main__":
    sys.exit(main())
