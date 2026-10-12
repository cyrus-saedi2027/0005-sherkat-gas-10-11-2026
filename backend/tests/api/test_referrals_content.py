from sqlalchemy import select

from app.modules.points.models import PointsLedger
from app.modules.referrals.models import Referral
from app.modules.users.models import UserDevice
from tests.api.test_readings import submit
from tests.conftest import make_staff, make_user, staff_headers, user_headers


def _refer(db, referrer, referee, device=None):
    from app.modules.referrals import service

    referrer.referral_code = referrer.referral_code or "CODE234"
    db.flush()
    return service.register(db, referee=referee, code=referrer.referral_code, device_id=device)


def _approve_first(client, db, u, op):
    rid = submit(client, u, color=(u.id * 7 % 255, 40, 90)).json()["id"]
    assert client.post(f"/api/v1/admin/readings/{rid}/approve", json={}, headers=staff_headers(op)).status_code == 200
    db.rollback()


def test_referral_paid_after_first_approved_reading(client, db):
    referrer = make_user(db, sn="1000000001", mobile="09120000001")
    referee = make_user(db, sn="1000000002", mobile="09120000002")
    op = make_staff(db, "operator")
    _refer(db, referrer, referee)
    db.commit()
    assert db.scalar(select(Referral)).status == "pending"
    _approve_first(client, db, referee, op)
    r = db.scalar(select(Referral))
    assert r.status == "rewarded"
    pay = db.scalar(select(PointsLedger).where(PointsLedger.user_id == referrer.id, PointsLedger.event_type == "referral_success"))
    assert pay.amount == 100
    mine = client.get("/api/v1/app/referrals", headers=user_headers(referrer)).json()
    assert mine["rewarded"] == 1 and mine["items"][0]["referee_name"] == "علی ر."


def test_shared_device_referral_is_suspicious_then_finance_review(client, db):
    referrer = make_user(db, sn="1000000001", mobile="09120000001")
    referee = make_user(db, sn="1000000002", mobile="09120000002")
    op = make_staff(db, "operator")
    fin = make_staff(db, "finance")
    db.add(UserDevice(user_id=referrer.id, device_id="phone-1"))
    db.flush()
    _refer(db, referrer, referee, device="phone-1")
    db.commit()
    _approve_first(client, db, referee, op)
    r = db.scalar(select(Referral))
    assert r.status == "suspicious" and r.signals.get("same_device_as_referrer")
    mine = client.get("/api/v1/app/referrals", headers=user_headers(referrer)).json()
    assert mine["items"][0]["status"] == "under_review"  # detection is not revealed
    q = client.get("/api/v1/admin/referrals?status=suspicious", headers=staff_headers(fin)).json()
    assert q["total"] == 1
    assert client.post(f"/api/v1/admin/referrals/{r.id}/review", json={"approve": True, "reason": "بررسی شد"},
                       headers=staff_headers(op)).status_code == 403
    d = client.post(f"/api/v1/admin/referrals/{r.id}/review", json={"approve": False, "reason": "یک نفر با دو حساب"},
                    headers=staff_headers(fin)).json()
    assert d["status"] == "rejected"


def test_monthly_referral_cap(client, db):
    admin = make_staff(db)
    op = make_staff(db, "operator")
    referrer = make_user(db, sn="1000000001", mobile="09120000001")
    db.commit()
    client.put("/api/v1/admin/settings", json={"values": {"fraud.referral_monthly_cap": 1}}, headers=staff_headers(admin))
    refs = [make_user(db, sn=f"20000000{i:02d}", mobile=f"091200001{i:02d}") for i in range(2)]
    for r in refs:
        _refer(db, referrer, r)
    db.commit()
    for r in refs:
        _approve_first(client, db, r, op)
    statuses = sorted(x.status for x in db.scalars(select(Referral)))
    assert statuses == ["capped", "rewarded"]


def test_content_targeting_by_tier(client, db):
    admin = make_staff(db, "operator")
    u = make_user(db)
    u.tier = "low_cost"
    db.commit()
    h = staff_headers(admin)
    a_all = client.post("/api/v1/admin/content", json={"title": "ده راهکار صرفه‌جویی", "body": "متن", "category": "tip"}, headers=h).json()
    a_high = client.post("/api/v1/admin/content", json={"title": "تعویض بخاری فرسوده", "body": "متن", "target_tiers": ["high_cost"]}, headers=h).json()
    a_low = client.post("/api/v1/admin/content", json={"title": "درزگیری پنجره", "body": "متن " * 400, "target_tiers": ["low_cost"]}, headers=h).json()
    assert client.get("/api/v1/app/content", headers=user_headers(u)).json() == []  # drafts are hidden
    for a in (a_all, a_high, a_low):
        client.post(f"/api/v1/admin/content/{a['id']}/status", json={"status": "published"}, headers=h)
    feed = client.get("/api/v1/app/content", headers=user_headers(u)).json()
    assert {x["title"] for x in feed} == {"ده راهکار صرفه‌جویی", "درزگیری پنجره"}
    assert client.get(f"/api/v1/app/content/{a_high['slug']}", headers=user_headers(u)).status_code == 404
    assert client.get(f"/api/v1/app/content/{a_low['slug']}", headers=user_headers(u)).json()["reading_minutes"] >= 2
    fin = make_staff(db, "finance")
    db.commit()
    assert client.post("/api/v1/admin/content", json={"title": "x" * 5}, headers=staff_headers(fin)).status_code == 403


def test_consumption_analysis(client, db):
    from datetime import date

    from app.modules.readings.models import MeterReading

    u = make_user(db, annual=6000)
    op = make_staff(db, "operator")
    db.add(MeterReading(user_id=u.id, subscriber_id=u.subscriber_id, period_key="1405-06", declared_value=1000,
                        approved_value=1000, reading_date=date(2026, 9, 12), status="approved"))
    db.commit()
    rid = submit(client, u, value="1400").json()["id"]
    client.post(f"/api/v1/admin/readings/{rid}/approve", json={}, headers=staff_headers(op))
    a = client.get("/api/v1/app/analytics/consumption", headers=user_headers(u)).json()
    assert len(a["periods"]) == 12 and a["periods"][-1]["period_key"] == "1405-07"
    assert round(a["periods"][-1]["reduction_pct"]) == 20
    assert round(a["totals"]["saved_m3"]) == 100 and a["totals"]["co2_saved_kg"] > 0
    assert a["baseline_years"] == [1402, 1403, 1404] and len(a["monthly_baseline"]) == 12
