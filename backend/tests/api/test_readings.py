"""Reading lifecycle (R12, R13, R15, R29, R43, R44) and the points it pays (R22, R23)."""

from datetime import date

from sqlalchemy import select

from app.core import clock
from app.modules.points.models import PointsLedger
from tests.conftest import jpeg_bytes, make_staff, make_user, staff_headers, user_headers

TODAY = "2026-10-12"  # 1405-07-20


def submit(client, u, value="1234", day=TODAY, photo=True, color=(200, 30, 30)):
    files = {"photo": ("meter.jpg", jpeg_bytes(color), "image/jpeg")} if photo else None
    return client.post("/api/v1/app/readings", data={"declared_value": value, "reading_date": day}, files=files,
                       headers=user_headers(u))


def test_submit_and_status(client, db):
    u = make_user(db)
    db.commit()
    cur = client.get("/api/v1/app/readings/current", headers=user_headers(u)).json()
    assert cur["period_key"] == "1405-07" and cur["can_submit"] and cur["submit_kind"] == "initial"
    r = submit(client, u, value="۱۲۳۴")  # Persian digits accepted
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["status"] == "pending" and body["declared_value"] == 1234 and body["period_label"] == "مهر ۱۴۰۵"
    assert body["photo_url"].startswith("/api/v1/files/")
    # one open reading per period
    assert submit(client, u).status_code == 409
    cur = client.get("/api/v1/app/readings/current", headers=user_headers(u)).json()
    assert cur["can_submit"] is False


def test_photo_validation(client, db):
    u = make_user(db)
    db.commit()
    assert submit(client, u, photo=False).status_code == 422  # photo required by default
    bad = client.post("/api/v1/app/readings", data={"declared_value": "1", "reading_date": TODAY},
                      files={"photo": ("x.jpg", b"<?php echo 1; ?>", "image/jpeg")}, headers=user_headers(u))
    assert bad.status_code == 415
    assert submit(client, u, day="2026-12-01").status_code == 422  # future date
    assert submit(client, u, day="2026-01-01").status_code == 422  # too old


def test_photo_is_reencoded_without_exif_and_served_signed(client, db):
    u = make_user(db)
    db.commit()
    r = submit(client, u).json()
    img = client.get(r["photo_url"])
    assert img.status_code == 200 and img.headers["content-type"] == "image/webp"
    assert img.headers["x-content-type-options"] == "nosniff"
    tampered = r["photo_url"].replace("sig=", "sig=0")
    assert client.get(tampered).status_code == 403
    clock.advance(hours=1)
    assert client.get(r["photo_url"]).status_code == 403  # expired


def test_approve_pays_once_per_period(client, db):
    u = make_user(db)
    op = make_staff(db, "operator")
    db.commit()
    rid = submit(client, u).json()["id"]
    a = client.post(f"/api/v1/admin/readings/{rid}/approve", json={}, headers=staff_headers(op))
    assert a.status_code == 200 and a.json()["status"] == "approved"
    # user asks for a review of the same period → new revision, approving it pays nothing more
    rid2 = submit(client, u, value="1240").json()
    assert rid2["kind"] == "review_request" and rid2["revision"] == 2
    client.post(f"/api/v1/admin/readings/{rid2['id']}/approve", json={}, headers=staff_headers(op))
    rows = db.scalars(select(PointsLedger).where(PointsLedger.event_type == "valid_reading")).all()
    assert len(rows) == 1 and rows[0].amount == 30 and rows[0].status == "pending"
    notes = client.get("/api/v1/app/notifications", headers=user_headers(u)).json()
    assert notes["unread"] >= 1 and notes["items"][0]["kind"] == "reading_approved"


def test_needs_correction_then_resubmit(client, db):
    from app.core import sms

    u = make_user(db)
    op = make_staff(db, "operator")
    db.commit()
    rid = submit(client, u).json()["id"]
    r = client.post(f"/api/v1/admin/readings/{rid}/needs-correction", json={"reason_code": "blurry_photo"},
                    headers=staff_headers(op))
    assert r.status_code == 200 and r.json()["status"] == "needs_correction"
    from app.core.sms import drain

    drain(db)
    db.commit()
    assert any("نیاز به اصلاح" in t for t in sms.DEV_LAST.values())  # R43: SMS to the user
    detail = client.get(f"/api/v1/app/readings/{rid}", headers=user_headers(u)).json()
    assert detail["reason_text"] == "تصویر کنتور واضح نیست." and detail["can_resubmit"]
    assert all(e["actor_name"] in (None, "کارشناس") for e in detail["events"])  # operator identity hidden
    new = submit(client, u, value="1235", color=(10, 200, 10)).json()
    assert new["kind"] == "correction" and new["revision"] == 2
    old = client.get(f"/api/v1/app/readings/{rid}", headers=user_headers(u)).json()
    assert old["is_current"] is False


def test_reason_validation_and_double_review(client, db):
    u = make_user(db)
    op = make_staff(db, "operator")
    db.commit()
    rid = submit(client, u).json()["id"]
    assert client.post(f"/api/v1/admin/readings/{rid}/reject", json={"reason_code": "nope"}, headers=staff_headers(op)).status_code == 422
    assert client.post(f"/api/v1/admin/readings/{rid}/reject", json={"reason_code": "other"}, headers=staff_headers(op)).status_code == 422
    assert client.post(f"/api/v1/admin/readings/{rid}/reject", json={"reason_code": "number_mismatch"}, headers=staff_headers(op)).status_code == 200
    assert client.post(f"/api/v1/admin/readings/{rid}/approve", json={}, headers=staff_headers(op)).status_code == 409


def test_value_correction_is_logged(client, db):
    u = make_user(db)
    op = make_staff(db, "operator")
    db.commit()
    rid = submit(client, u, value="1234").json()["id"]
    r = client.post(f"/api/v1/admin/readings/{rid}/approve", json={"approved_value": 1243, "note": "رقم آخر اشتباه خوانده شده"},
                    headers=staff_headers(op)).json()
    assert r["approved_value"] == 1243
    actions = [e["action"] for e in r["events"]]
    assert "value_corrected" in actions and "approved" in actions
    vc = next(e for e in r["events"] if e["action"] == "value_corrected")
    assert vc["old_value"] == 1234 and vc["new_value"] == 1243 and vc["actor_name"]
    from app.modules.audit.models import AuditLog

    assert db.scalar(select(AuditLog).where(AuditLog.action == "reading.approve", AuditLog.entity_id == str(rid)))


def test_ambassador_cannot_review(client, db):
    u = make_user(db)
    amb = make_staff(db, "ambassador")
    fin = make_staff(db, "finance")
    db.commit()
    rid = submit(client, u).json()["id"]
    for st in (amb, fin):
        assert client.post(f"/api/v1/admin/readings/{rid}/approve", json={}, headers=staff_headers(st)).status_code == 403


def test_consumption_and_reduction_points(client, db):
    """Previous month approved at 1000; this month 1100 over 30 days vs baseline 500/month → 80% drop → flagged, then approved."""
    from app.modules.readings.models import MeterReading

    u = make_user(db, annual=6000)  # 500 m³ per month baseline
    op = make_staff(db, "operator")
    prev = MeterReading(user_id=u.id, subscriber_id=u.subscriber_id, period_key="1405-06", declared_value=1000,
                        approved_value=1000, reading_date=date(2026, 9, 12), status="approved")
    db.add(prev)
    db.commit()
    r = submit(client, u, value="1400").json()  # 400 m³ in 30 days ≈ 400 → 20% reduction
    assert r["status"] == "pending"
    a = client.post(f"/api/v1/admin/readings/{r['id']}/approve", json={}, headers=staff_headers(op)).json()
    assert round(a["consumption_m3"]) == 400 and round(a["reduction_pct"]) == 20
    red = db.scalar(select(PointsLedger).where(PointsLedger.event_type == "consumption_reduction"))
    assert red is not None and red.amount == 200  # 10 per % × 20 = 200 (= monthly cap)


def test_anomalies_route_to_flagged_queue(client, db):
    from app.modules.readings.models import MeterReading

    u = make_user(db, annual=6000)
    op = make_staff(db, "operator")
    db.add(MeterReading(user_id=u.id, subscriber_id=u.subscriber_id, period_key="1405-06", declared_value=5000,
                        approved_value=5000, reading_date=date(2026, 9, 12), status="approved"))
    db.commit()
    r = submit(client, u, value="4900").json()  # meter went backwards
    assert r["status"] == "flagged"
    q = client.get("/api/v1/admin/readings?status=flagged", headers=staff_headers(op)).json()
    assert q["total"] == 1 and {f["code"] for f in q["items"][0]["flags"]} >= {"meter_rollback"}


def test_duplicate_photo_flag(client, db):
    """Same photo bytes sent for two different subscribers → flagged for manual review (R15)."""
    u1 = make_user(db, sn="1000000001", mobile="09120000011")
    u2 = make_user(db, sn="1000000002", mobile="09120000012")
    db.commit()
    assert submit(client, u1).json()["status"] == "pending"
    second = submit(client, u2).json()
    assert second["status"] == "flagged"
    op = make_staff(db, "operator")
    db.commit()
    d = client.get(f"/api/v1/admin/readings/{second['id']}", headers=staff_headers(op)).json()
    assert "duplicate_photo" in {f["code"] for f in d["flags"]}


def test_queue_filters_and_detail(client, db):
    from tests.conftest import make_region

    reg = make_region(db)
    u = make_user(db, region_id=reg.id)
    op = make_staff(db, "operator")
    db.commit()
    rid = submit(client, u).json()["id"]
    q = client.get(f"/api/v1/admin/readings?region_id={reg.id}&subscription_no=1234", headers=staff_headers(op)).json()
    assert q["total"] == 1 and q["items"][0]["region_name"] == "منطقه ۲"
    d = client.get(f"/api/v1/admin/readings/{rid}", headers=staff_headers(op)).json()
    assert len(d["history"]) == 36 and d["baseline_for_period"] == 500  # R44: 3-year history visible
    c = client.post(f"/api/v1/admin/readings/{rid}/claim", headers=staff_headers(op)).json()
    assert c["claimed_by_me"]
    stats = client.get("/api/v1/admin/readings/stats", headers=staff_headers(op)).json()
    assert stats["pending"] == 1
