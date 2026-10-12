"""Ambassador workflow end-to-end (R14–R19, R30, R38, R43) and row-level security."""

from datetime import UTC, datetime, timedelta

from sqlalchemy import select

from app.modules.cases.models import Case
from app.modules.points.models import PointsLedger
from tests.api.test_readings import submit
from tests.conftest import jpeg_bytes, make_region, make_staff, make_user, staff_headers, user_headers


def _approved_reading_opens_case(client, db, region_id=None, **kw):
    u = make_user(db, region_id=region_id, **kw)
    op = make_staff(db, "operator")
    db.commit()
    rid = submit(client, u).json()["id"]
    client.post(f"/api/v1/admin/readings/{rid}/approve", json={}, headers=staff_headers(op))
    db.rollback()
    c = db.scalar(select(Case).where(Case.user_id == u.id))
    # End the read transaction: a stale WAL snapshot cannot later be upgraded to a write in SQLite.
    db.commit()
    return u, c


def test_first_approval_opens_case_and_assigns_by_region(client, db):
    root = make_region(db, "R2", "منطقه ۲")
    z1 = make_region(db, "Z1", "گلسار", parent_id=root.id)
    z2 = make_region(db, "Z2", "معلم", parent_id=root.id)
    far = make_staff(db, "ambassador", service_region_ids=[z2.id])
    near = make_staff(db, "ambassador", service_region_ids=[z1.id])
    db.commit()
    u, c = _approved_reading_opens_case(client, db, region_id=z1.id)
    assert c is not None and c.status == "assigned" and c.ambassador_id == near.id and c.assignment_method == "auto"
    assert far.id != c.ambassador_id


def test_assignment_balances_workload(client, db):
    a1 = make_staff(db, "ambassador")
    a2 = make_staff(db, "ambassador")
    db.commit()
    _, c1 = _approved_reading_opens_case(client, db, sn="1000000001", mobile="09120000001")
    _, c2 = _approved_reading_opens_case(client, db, sn="1000000002", mobile="09120000002")
    assert {c1.ambassador_id, c2.ambassador_id} == {a1.id, a2.id}


def test_no_ambassador_leaves_case_unassigned(client, db):
    _, c = _approved_reading_opens_case(client, db)
    assert c.status == "new" and c.ambassador_id is None


def test_full_high_cost_flow_with_consent_and_points(client, db):
    amb = make_staff(db, "ambassador")
    tech = make_staff(db, "technician")
    db.commit()
    u, c = _approved_reading_opens_case(client, db)
    h = staff_headers(amb)
    base = f"/api/v1/admin/cases/{c.id}"
    # checklist before the phone call is refused (R16: call first)
    r = client.put(f"{base}/checklist", json={"insulation": "none"}, headers=h)
    assert r.status_code == 409
    assert client.post(f"{base}/calls", json={"outcome": "no_answer"}, headers=h).status_code == 201
    assert client.get(base, headers=h).json()["status"] == "assigned"
    client.post(f"{base}/calls", json={"outcome": "reached", "note": "هماهنگ شد"}, headers=h)
    checklist = {"floor_area_m2": 180, "built_area_m2": 200, "residents_count": 4, "building_type": "villa",
                 "heating_equipment": [{"type": "heater", "count": 3, "condition": "poor", "age_years": 18}],
                 "insulation": "none", "window_seals": "poor", "chimney_status": "needs_repair"}
    d = client.put(f"{base}/checklist", json=checklist, headers=h).json()
    assert d["suggested_tier"] == "high_cost" and d["status"] == "contacted"
    # overriding the suggestion needs a reason
    assert client.post(f"{base}/evaluate", json={"tier": "low_cost", "needs_field_visit": True}, headers=h).status_code == 422
    d = client.post(f"{base}/evaluate", json={"tier": "high_cost", "needs_field_visit": True}, headers=h).json()
    assert d["status"] == "evaluated" and d["tier"] == "high_cost"
    me = client.get("/api/v1/app/me", headers=user_headers(u)).json()
    assert me["tier"] == "high_cost"
    start = datetime(2026, 10, 14, 6, 30, tzinfo=UTC)
    d = client.post(f"{base}/visits", json={"start": start.isoformat(), "end": (start + timedelta(hours=1)).isoformat()}, headers=h).json()
    assert d["status"] == "visit_scheduled" and d["next_visit_at"]
    cal = client.get("/api/v1/admin/cases/calendar?date_from=2026-10-13T00:00:00Z&date_to=2026-10-20T00:00:00Z", headers=h).json()
    assert len(cal) == 1 and cal[0]["case_id"] == c.id
    client.post(f"{base}/photos", data={"phase": "before"}, files={"file": ("b.jpg", jpeg_bytes((1, 2, 3)), "image/jpeg")}, headers=h)
    d = client.post(f"{base}/visit-done", json={"outcome": "done"}, headers=h).json()
    assert d["status"] == "visited"
    est = {"items": [{"title": "تعویض بخاری", "qty": 2, "unit_cost_rial": 40_000_000}, {"title": "عایق‌کاری", "qty": 1, "unit_cost_rial": 20_000_000}]}
    d = client.post(f"{base}/estimates", json=est, headers=h).json()
    e = d["estimates"][0]
    assert e["total_cost_rial"] == 100_000_000 and e["subscriber_share_pct"] == 30
    assert e["subscriber_share_rial"] == 30_000_000 and e["program_share_rial"] == 70_000_000  # R19: 30/70
    assert d["status"] == "awaiting_consent"
    # cannot execute without consent
    assert client.post(f"{base}/executed", json={}, headers=h).status_code == 409
    uc = client.get("/api/v1/app/case", headers=user_headers(u)).json()
    assert uc["estimate"]["subscriber_share_rial"] == 30_000_000 and uc["status"] == "awaiting_consent"
    assert all(t["actor_id"] is None and t["note"] is None for t in uc["timeline"])  # no staff internals leak
    uc = client.post("/api/v1/app/case/consent", json={"accept": True}, headers=user_headers(u)).json()
    assert uc["status"] == "consent_given"
    # after-photos are required before execution is reported
    assert client.post(f"{base}/executed", json={}, headers=h).json()["error"]["code"] == "photos_required"
    client.post(f"{base}/photos", data={"phase": "after"}, files={"file": ("a.jpg", jpeg_bytes((9, 8, 7)), "image/jpeg")}, headers=h)
    assert client.post(f"{base}/executed", json={}, headers=h).json()["status"] == "pending_final_approval"
    # ambassadors cannot give the final approval
    assert client.post(f"{base}/final-approve", json={}, headers=h).status_code == 403
    d = client.post(f"{base}/final-approve", json={"note": "تأیید شد"}, headers=staff_headers(tech)).json()
    assert d["status"] == "completed"
    db.rollback()
    pts = {e.event_type: e.amount for e in db.scalars(select(PointsLedger).where(PointsLedger.user_id == u.id))}
    assert pts["ambassador_cooperation"] == 50 and pts["optimization_executed"] == 50  # R23 + flowchart +50


def test_no_cost_flow_education_only(client, db):
    amb = make_staff(db, "ambassador")
    tech = make_staff(db, "technician")
    db.commit()
    u, c = _approved_reading_opens_case(client, db)
    h, base = staff_headers(amb), f"/api/v1/admin/cases/{c.id}"
    client.post(f"{base}/calls", json={"outcome": "reached"}, headers=h)
    good = {"floor_area_m2": 90, "heating_equipment": [{"type": "package", "count": 1, "condition": "good", "age_years": 3}],
            "insulation": "full", "window_seals": "good", "chimney_status": "ok"}
    assert client.put(f"{base}/checklist", json=good, headers=h).json()["suggested_tier"] == "no_cost"
    d = client.post(f"{base}/evaluate", json={"tier": "no_cost", "needs_field_visit": True}, headers=h).json()
    assert d["needs_field_visit"] is False  # no-cost never needs a visit (R17)
    notes = client.get("/api/v1/app/notifications", headers=user_headers(u)).json()["items"]
    assert any(n["kind"] == "tier_assigned" and n["data"]["route"] == "/learn" for n in notes)
    assert client.post(f"{base}/visits", json={"start": "2026-10-14T06:30:00Z", "end": "2026-10-14T07:30:00Z"}, headers=h).status_code == 409
    assert client.post(f"{base}/submit-final", json={}, headers=h).json()["status"] == "pending_final_approval"
    client.post(f"{base}/final-approve", json={}, headers=staff_headers(tech))
    db.rollback()
    events = {e.event_type for e in db.scalars(select(PointsLedger).where(PointsLedger.user_id == u.id))}
    assert "ambassador_cooperation" in events and "optimization_executed" not in events


def test_low_cost_within_free_cap_needs_no_consent(client, db):
    amb = make_staff(db, "ambassador")
    db.commit()
    _, c = _approved_reading_opens_case(client, db)
    h, base = staff_headers(amb), f"/api/v1/admin/cases/{c.id}"
    client.post(f"{base}/calls", json={"outcome": "reached"}, headers=h)
    client.put(f"{base}/checklist", json={"insulation": "partial", "window_seals": "poor"}, headers=h)
    client.post(f"{base}/evaluate", json={"tier": "low_cost", "needs_field_visit": True}, headers=h)
    client.post(f"{base}/visits", json={"start": "2026-10-14T06:30:00Z", "end": "2026-10-14T07:30:00Z"}, headers=h)
    client.post(f"{base}/visit-done", json={"outcome": "done"}, headers=h)
    d = client.post(f"{base}/estimates", json={"items": [{"title": "نوار درزگیر", "qty": 10, "unit_cost_rial": 300_000}]}, headers=h).json()
    assert d["estimates"][0]["subscriber_share_rial"] == 0 and d["status"] == "in_execution"


def test_ambassador_sees_only_own_cases(client, db):
    a1 = make_staff(db, "ambassador")
    db.commit()
    _, c = _approved_reading_opens_case(client, db)
    a2 = make_staff(db, "ambassador")
    db.commit()
    assert c.ambassador_id == a1.id
    assert client.get(f"/api/v1/admin/cases/{c.id}", headers=staff_headers(a2)).status_code == 404
    assert client.post(f"/api/v1/admin/cases/{c.id}/calls", json={"outcome": "reached"}, headers=staff_headers(a2)).status_code == 404
    assert client.get("/api/v1/admin/cases", headers=staff_headers(a2)).json()["total"] == 0
    assert client.get("/api/v1/admin/cases", headers=staff_headers(a1)).json()["total"] == 1
    assert client.post(f"/api/v1/admin/cases/{c.id}/assign", json={"ambassador_id": a2.id}, headers=staff_headers(a1)).status_code == 403


def test_manual_reassign_and_visit_conflict(client, db):
    a1 = make_staff(db, "ambassador")
    tech = make_staff(db, "technician")
    db.commit()
    _, c = _approved_reading_opens_case(client, db, sn="1000000001", mobile="09120000001")
    _, c2 = _approved_reading_opens_case(client, db, sn="1000000002", mobile="09120000002")
    for case in (c, c2):
        b = f"/api/v1/admin/cases/{case.id}"
        client.post(f"{b}/calls", json={"outcome": "reached"}, headers=staff_headers(a1))
        client.put(f"{b}/checklist", json={"insulation": "none", "window_seals": "poor"}, headers=staff_headers(a1))
        client.post(f"{b}/evaluate", json={"tier": "low_cost", "needs_field_visit": True}, headers=staff_headers(a1))
    slot = {"start": "2026-10-14T06:30:00Z", "end": "2026-10-14T07:30:00Z"}
    assert client.post(f"/api/v1/admin/cases/{c.id}/visits", json=slot, headers=staff_headers(a1)).status_code == 200
    r = client.post(f"/api/v1/admin/cases/{c2.id}/visits", json=slot, headers=staff_headers(a1))
    assert r.status_code == 409 and r.json()["error"]["code"] == "visit_conflict"
    a2 = make_staff(db, "ambassador")
    db.commit()
    d = client.post(f"/api/v1/admin/cases/{c2.id}/assign", json={"ambassador_id": a2.id}, headers=staff_headers(tech)).json()
    assert d["ambassador_id"] == a2.id and d["assignment_method"] == "manual"


def test_below_threshold_after_rule_change_blocks_case(client, db):
    admin = make_staff(db)
    make_staff(db, "ambassador")
    u = make_user(db, annual=4000)
    db.commit()
    client.put("/api/v1/admin/settings", json={"values": {"eligibility.threshold_m3": 5000}}, headers=staff_headers(admin))
    rid = submit(client, u).json()["id"]
    client.post(f"/api/v1/admin/readings/{rid}/approve", json={}, headers=staff_headers(admin))
    db.rollback()
    assert db.scalar(select(Case).where(Case.user_id == u.id)) is None
    assert client.get("/api/v1/app/me", headers=user_headers(u)).json()["eligibility"] == "below_threshold"


def test_case_dashboard_kpis(client, db):
    make_staff(db, "ambassador")
    admin = make_staff(db)
    db.commit()
    _approved_reading_opens_case(client, db)
    k = {x["key"]: x["value"] for x in client.get("/api/v1/admin/dashboard", headers=staff_headers(admin)).json()["kpis"]}
    assert k["cases_referred"] == 1 and k["cases_open"] == 1
