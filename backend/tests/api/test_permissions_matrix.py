"""Every role × every protected endpoint: allowed iff the role holds the permission (R26, R34)."""

import pytest

from app.core.rbac import ROLE_PERMISSIONS, P, Role
from tests.conftest import make_staff, staff_headers

# (method, path, permission, json body)
ENDPOINTS: list[tuple[str, str, P, dict | None]] = [
    ("GET", "/api/v1/admin/dashboard", P.DASHBOARD_VIEW, None),
    ("GET", "/api/v1/admin/subscribers", P.SUBSCRIBERS_VIEW, None),
    ("GET", "/api/v1/admin/subscribers/import/batches", P.SUBSCRIBERS_IMPORT, None),
    ("GET", "/api/v1/admin/subscribers/import/template", P.SUBSCRIBERS_IMPORT, None),
    ("GET", "/api/v1/admin/users", P.USERS_VIEW, None),
    ("GET", "/api/v1/admin/readings", P.READINGS_VIEW, None),
    ("GET", "/api/v1/admin/readings/stats", P.READINGS_VIEW, None),
    ("GET", "/api/v1/admin/points/rules", P.POINTS_VIEW, None),
    ("GET", "/api/v1/admin/points/ledger", P.POINTS_VIEW, None),
    ("PUT", "/api/v1/admin/points/rules/signup", P.POINTS_RULES_EDIT, {"points": 120, "is_active": True}),
    ("GET", "/api/v1/admin/settings", P.SETTINGS_VIEW, None),
    ("GET", "/api/v1/admin/staff", P.STAFF_VIEW, None),
    ("GET", "/api/v1/admin/staff/roles", P.STAFF_VIEW, None),
    ("POST", "/api/v1/admin/staff/access-review", P.ACCESS_REVIEW_PERFORM, {"notes": "q"}),
    ("GET", "/api/v1/admin/audit/logs", P.AUDIT_VIEW, None),
    ("GET", "/api/v1/admin/audit/logins", P.AUDIT_VIEW, None),
    ("GET", "/api/v1/admin/regions", P.DASHBOARD_VIEW, None),
    ("POST", "/api/v1/admin/regions", P.SUBSCRIBERS_EDIT, {"name": "ناحیه", "code": "ZX"}),
]


@pytest.mark.parametrize("role", [r.value for r in Role])
@pytest.mark.parametrize("method,path,perm,body", ENDPOINTS, ids=[f"{m} {p}" for m, p, _, _ in ENDPOINTS])
def test_matrix(client, db, role, method, path, perm, body):
    st = make_staff(db, role)
    db.commit()
    r = client.request(method, path, json=body, headers=staff_headers(st))
    allowed = perm in ROLE_PERMISSIONS[Role(role)]
    if allowed:
        assert r.status_code < 400, f"{role} should reach {method} {path}: {r.status_code} {r.text}"
    else:
        assert r.status_code == 403, f"{role} must NOT reach {method} {path}: {r.status_code}"
        assert r.json()["error"]["code"] == "forbidden"


def test_anonymous_gets_401_everywhere(client):
    for method, path, _, body in ENDPOINTS:
        r = client.request(method, path, json=body)
        assert r.status_code == 401, (method, path, r.status_code)


def test_operator_cannot_change_finance_settings(client, db):
    op = make_staff(db, "operator")
    admin = make_staff(db, "super_admin")
    fin = make_staff(db, "finance")
    db.commit()
    r = client.put("/api/v1/admin/settings", json={"values": {"finance.point_rial_rate": 5}}, headers=staff_headers(op))
    assert r.status_code == 403
    # operator has settings.view but not settings.edit → even non-finance keys are refused
    r = client.put("/api/v1/admin/settings", json={"values": {"otp.ttl_seconds": 90}}, headers=staff_headers(op))
    assert r.status_code == 403
    # finance may edit finance keys but not general ones
    assert client.put("/api/v1/admin/settings", json={"values": {"finance.point_rial_rate": 2000}}, headers=staff_headers(fin)).status_code == 200
    assert client.put("/api/v1/admin/settings", json={"values": {"otp.ttl_seconds": 90}}, headers=staff_headers(fin)).status_code == 403
    r = client.put("/api/v1/admin/settings", json={"values": {"eligibility.threshold_m3": "abc", "nope.key": 1}},
                   headers=staff_headers(admin))
    assert r.status_code == 422 and set(r.json()["error"]["details"]["fields"]) == {"eligibility.threshold_m3", "nope.key"}
    listing = client.get("/api/v1/admin/settings", headers=staff_headers(op)).json()
    fin_row = next(x for x in listing if x["key"] == "finance.point_rial_rate")
    assert fin_row["value"] == 2000 and fin_row["editable"] is False


def test_settings_changes_are_audited(client, db):
    from sqlalchemy import select

    from app.modules.audit.models import AuditLog

    admin = make_staff(db)
    db.commit()
    client.put("/api/v1/admin/settings", json={"values": {"eligibility.threshold_m3": 4000}}, headers=staff_headers(admin))
    log = db.scalar(select(AuditLog).where(AuditLog.action == "settings.update"))
    assert log.before == {"value": 3500} and log.after == {"value": 4000} and log.actor_id == admin.id
