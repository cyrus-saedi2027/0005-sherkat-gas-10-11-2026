from app.core import clock
from tests.conftest import PASSWORD, make_staff, staff_headers


def test_staff_login_and_me(client, db):
    make_staff(db, "operator", username="op1")
    db.commit()
    r = client.post("/api/v1/admin/auth/login", json={"username": "OP1", "password": PASSWORD})
    assert r.status_code == 200 and r.json()["otp_required"] is False
    h = {"Authorization": f"Bearer {r.json()['tokens']['access_token']}"}
    me = client.get("/api/v1/admin/auth/me", headers=h).json()
    assert me["roles"] == ["operator"] and "readings.review" in me["permissions"]
    assert "settings.finance_edit" not in me["permissions"]


def test_staff_lockout_after_failures(client, db):
    make_staff(db, "operator", username="op2")
    db.commit()
    for _ in range(5):
        assert client.post("/api/v1/admin/auth/login", json={"username": "op2", "password": "wrong-pass1"}).status_code == 401
    r = client.post("/api/v1/admin/auth/login", json={"username": "op2", "password": PASSWORD})
    assert r.status_code == 423
    clock.advance(minutes=16)
    assert client.post("/api/v1/admin/auth/login", json={"username": "op2", "password": PASSWORD}).status_code == 200


def test_unknown_and_wrong_password_same_answer(client, db):
    make_staff(db, "operator", username="op3")
    db.commit()
    a = client.post("/api/v1/admin/auth/login", json={"username": "op3", "password": "nope-nope1"})
    b = client.post("/api/v1/admin/auth/login", json={"username": "ghost", "password": "nope-nope1"})
    assert a.status_code == b.status_code == 401 and a.json() == b.json()


def test_staff_2fa(client, db):
    from app.core import crypto

    st = make_staff(db, "finance", username="fin", otp_2fa_enabled=True)
    st.mobile_enc = crypto.encrypt("09127770000")
    db.commit()
    r = client.post("/api/v1/admin/auth/login", json={"username": "fin", "password": PASSWORD}).json()
    assert r["otp_required"] and r["tokens"] is None
    v = client.post("/api/v1/admin/auth/login/verify", json={"challenge_id": r["challenge_id"], "code": r["dev_code"]})
    assert v.status_code == 200


def test_deactivation_and_role_change_take_effect_immediately(client, db):
    admin = make_staff(db)
    op = make_staff(db, "operator")
    db.commit()
    h = staff_headers(op)
    assert client.get("/api/v1/admin/readings", headers=h).status_code == 200
    client.patch(f"/api/v1/admin/staff/{op.id}", json={"roles": ["ambassador"]}, headers=staff_headers(admin))
    assert client.get("/api/v1/admin/readings", headers=h).status_code == 403  # same token, new roles
    client.patch(f"/api/v1/admin/staff/{op.id}", json={"is_active": False}, headers=staff_headers(admin))
    assert client.get("/api/v1/admin/auth/me", headers=h).status_code == 401


def test_admin_cannot_lock_themselves_out(client, db):
    admin = make_staff(db)
    db.commit()
    r = client.patch(f"/api/v1/admin/staff/{admin.id}", json={"is_active": False}, headers=staff_headers(admin))
    assert r.status_code == 409


def test_user_token_cannot_call_admin(client, db):
    from tests.conftest import make_user, user_headers

    u = make_user(db)
    db.commit()
    assert client.get("/api/v1/admin/readings", headers=user_headers(u)).status_code == 403
