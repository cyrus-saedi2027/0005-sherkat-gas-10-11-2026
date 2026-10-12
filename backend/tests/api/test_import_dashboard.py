import io

from openpyxl import Workbook
from sqlalchemy import func, select

from app.modules.subscribers.models import ConsumptionHistory, Subscriber
from tests.conftest import make_region, make_staff, staff_headers


def _xlsx(sub_rows, cons_rows=None) -> bytes:
    wb = Workbook()
    ws = wb.active
    ws.title = "مشترکین"
    ws.append(["شماره اشتراک", "شماره موبایل", "نام و نام خانوادگی", "کد ناحیه"])
    for r in sub_rows:
        ws.append(r)
    if cons_rows is not None:
        ws2 = wb.create_sheet("مصرف")
        ws2.append(["شماره اشتراک", "سال", "ماه", "مصرف"])
        for r in cons_rows:
            ws2.append(r)
    b = io.BytesIO()
    wb.save(b)
    return b.getvalue()


def _upload(client, h, data, name="list.xlsx"):
    return client.post("/api/v1/admin/subscribers/import", files={"file": (name, data, "application/octet-stream")}, headers=h)


def test_import_validate_then_commit_idempotent(client, db):
    make_region(db, code="R2-Z1", name="گلسار")
    op = make_staff(db, "operator")
    db.commit()
    h = staff_headers(op)
    cons = [["4000000001", y, m, 400] for y in (1402, 1403, 1404) for m in range(1, 13)]
    data = _xlsx([["4000000001", "۰۹۱۲۱۲۳۴۵۶۷", "علي كاظمي", "R2-Z1"], ["4000000002", "+989121234568", "سارا", "r2-z1"]], cons)
    b = _upload(client, h, data).json()
    assert b["status"] == "validated" and b["error_count"] == 0
    assert b["summary"]["subscribers_new"] == 2 and b["summary"]["history_rows"] == 36
    assert db.scalar(select(func.count()).select_from(Subscriber)) == 0  # dry run wrote nothing
    c = client.post(f"/api/v1/admin/subscribers/import/{b['id']}/commit", json={}, headers=h).json()
    assert c["status"] == "committed"
    db.rollback()  # end the test session's read snapshot so it sees the API's commit
    s = db.scalar(select(Subscriber).where(Subscriber.subscription_no == "4000000001"))
    assert s.full_name == "علی کاظمی" and s.baseline_annual_m3 == 4800  # normalised Arabic letters; 12×400
    assert client.post(f"/api/v1/admin/subscribers/import/{b['id']}/commit", json={}, headers=h).status_code == 409
    # same file again → updates, no duplicates
    b2 = _upload(client, h, data).json()
    client.post(f"/api/v1/admin/subscribers/import/{b2['id']}/commit", json={}, headers=h)
    db.rollback()
    assert db.scalar(select(func.count()).select_from(Subscriber)) == 2
    assert db.scalar(select(func.count()).select_from(ConsumptionHistory)) == 36
    # the imported subscriber can now sign up
    r = client.post("/api/v1/app/auth/signup/start", json={"mobile": "09121234567", "subscription_no": "4000000001"})
    assert r.status_code == 200


def test_import_row_errors(client, db):
    op = make_staff(db, "operator")
    db.commit()
    h = staff_headers(op)
    data = _xlsx([["12", "09121234567", "x", None], ["4000000003", "12345", "y", None], ["4000000004", "09121111111", "z", "NOPE"],
                  ["4000000005", "09121111112", "ok", None], ["4000000005", "09121111113", "dup", None]],
                 [["4000000005", 1404, 13, 100], ["4000000005", 1404, 1, -5], ["9999999999", 1404, 1, 5]])
    b = _upload(client, h, data).json()
    msgs = {(e["row"], e["column"]) for e in b["errors"]}
    assert b["error_count"] == 7 and (2, "شماره اشتراک") in msgs and (3, "شماره موبایل") in msgs and (4, "کد ناحیه") in msgs
    assert client.post(f"/api/v1/admin/subscribers/import/{b['id']}/commit", json={}, headers=h).status_code == 409
    ok = client.post(f"/api/v1/admin/subscribers/import/{b['id']}/commit", json={"skip_errors": True}, headers=h)
    assert ok.status_code == 200 and ok.json()["summary"]["subscribers_created"] == 1


def test_import_rejects_non_xlsx(client, db):
    op = make_staff(db, "operator")
    db.commit()
    assert _upload(client, staff_headers(op), b"MZ\x90\x00 not excel", "evil.xlsx").status_code == 415
    assert _upload(client, staff_headers(op), b"a,b", "list.csv").status_code == 415


def test_template_download(client, db):
    op = make_staff(db, "operator")
    db.commit()
    r = client.get("/api/v1/admin/subscribers/import/template", headers=staff_headers(op))
    assert r.status_code == 200 and r.content[:2] == b"PK"


def test_dashboard_kpis_by_role(client, db):
    from tests.conftest import make_subscriber, make_user

    make_user(db)
    make_subscriber(db, sn="2222222222", mobile="09120000002", annual=1000)
    admin = make_staff(db)
    amb = make_staff(db, "ambassador")
    db.commit()
    d = client.get("/api/v1/admin/dashboard", headers=staff_headers(admin)).json()
    k = {x["key"]: x["value"] for x in d["kpis"]}
    assert k["subscribers_total"] == 2 and k["subscribers_eligible"] == 1 and k["users_registered"] == 1
    assert len(d["series"][0]["points"]) == 30
    a = client.get("/api/v1/admin/dashboard", headers=staff_headers(amb)).json()
    assert "subscribers_total" not in {x["key"] for x in a["kpis"]}  # ambassadors see only their own blocks


def test_pagination_cap(client, db):
    op = make_staff(db, "operator")
    db.commit()
    assert client.get("/api/v1/admin/users?size=101", headers=staff_headers(op)).status_code == 422
    assert client.get("/api/v1/admin/users?size=100", headers=staff_headers(op)).status_code == 200


def test_body_size_limit(client, db):
    op = make_staff(db, "operator")
    db.commit()
    big = "x" * 1_100_000
    r = client.put("/api/v1/admin/settings", content=f'{{"values": {{"support.phone": "{big}"}}}}',
                   headers={**staff_headers(op), "content-type": "application/json"})
    assert r.status_code == 413


def test_security_headers(client):
    r = client.get("/api/v1/health")
    assert r.headers["x-content-type-options"] == "nosniff" and r.headers["x-frame-options"] == "DENY"
    assert r.headers["cache-control"] == "no-store" and "x-request-id" in r.headers
