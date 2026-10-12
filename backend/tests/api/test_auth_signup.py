"""Signup / login flows (R07–R11) and the no-enumeration guarantee (R09)."""

from app.core.errors import NOT_ELIGIBLE_FA
from tests.conftest import PASSWORD, make_subscriber, make_user


def _start(client, mobile="09121112233", sn="1234567890", **kw):
    return client.post("/api/v1/app/auth/signup/start", json={"mobile": mobile, "subscription_no": sn, **kw})


def _full_signup(client, db, **kw):
    r = _start(client, **kw)
    assert r.status_code == 200, r.text
    ch = r.json()
    v = client.post("/api/v1/app/auth/signup/verify", json={"challenge_id": ch["challenge_id"], "code": ch["dev_code"]})
    assert v.status_code == 200 and v.json()["status"] == "verified", v.text
    c = client.post("/api/v1/app/auth/signup/complete", json={"signup_token": v.json()["signup_token"], "accept_terms": True,
                                                              "accept_privacy": True, "login_method": "otp", "device_id": "dev-1"})
    assert c.status_code == 200, c.text
    return c.json()


def test_full_signup_awards_points_once(client, db):
    make_subscriber(db)
    db.commit()
    tok = _full_signup(client, db)
    h = {"Authorization": f"Bearer {tok['access_token']}"}
    bal = client.get("/api/v1/app/points/balance", headers=h).json()
    assert bal["pending"] == 100 and bal["available"] == 0
    me = client.get("/api/v1/app/me", headers=h).json()
    assert me["subscription_no"] == "1234567890" and me["mobile_masked"] == "0912***2233"
    # Signing up again with the same subscriber logs in instead of creating a second account
    ch = _start(client).json()
    v = client.post("/api/v1/app/auth/signup/verify", json={"challenge_id": ch["challenge_id"], "code": ch["dev_code"]}).json()
    assert v["status"] == "logged_in"
    assert client.get("/api/v1/app/points/balance", headers=h).json()["pending"] == 100


def test_persian_digits_and_prefixes_normalised(client, db):
    make_subscriber(db)
    db.commit()
    r = _start(client, mobile="+98 912 111 2233", sn="۱۲۳۴۵۶۷۸۹۰")
    assert r.status_code == 200, r.text


def test_not_eligible_paths_are_indistinguishable(client, db):
    make_subscriber(db, sn="1111111111", mobile="09120000001", annual=6000)
    make_subscriber(db, sn="2222222222", mobile="09120000002", annual=2000)  # below 3500
    make_subscriber(db, sn="3333333333", mobile="09120000003", annual=6000, active=False)
    db.commit()
    cases = [("09120000009", "1111111111"),  # wrong mobile for a real subscription
             ("09120000001", "9999999999"),  # unknown subscription
             ("09120000002", "2222222222"),  # below threshold
             ("09120000003", "3333333333")]  # inactive
    bodies = set()
    for m, sn in cases:
        r = _start(client, mobile=m, sn=sn)
        assert r.status_code == 422
        assert r.json()["error"]["code"] == "not_eligible"
        assert r.json()["error"]["message"] == NOT_ELIGIBLE_FA
        bodies.add(r.text)
    assert len(bodies) == 1  # byte-identical answers: nothing to learn from the response


def test_threshold_is_a_setting(client, db):
    from tests.conftest import make_staff, staff_headers

    make_subscriber(db, sn="2222222222", mobile="09120000002", annual=3000)
    admin = make_staff(db)
    db.commit()
    assert _start(client, mobile="09120000002", sn="2222222222").status_code == 422
    r = client.put("/api/v1/admin/settings", json={"values": {"eligibility.threshold_m3": 2500}}, headers=staff_headers(admin))
    assert r.status_code == 200, r.text
    from app.core import clock

    clock.advance(seconds=61)  # the ineligible attempt is subject to the same resend cooldown (no oracle)
    assert _start(client, mobile="09120000002", sn="2222222222").status_code == 200


def test_otp_wrong_code_attempts_and_lock(client, db):
    make_subscriber(db)
    db.commit()
    ch = _start(client).json()
    for i in range(5):
        r = client.post("/api/v1/app/auth/signup/verify", json={"challenge_id": ch["challenge_id"], "code": "00000" if ch["dev_code"] != "00000" else "11111"})
        assert r.status_code == 400 and r.json()["error"]["code"] == "otp_wrong"
        assert r.json()["error"]["details"]["attempts_left"] == 4 - i
    r = client.post("/api/v1/app/auth/signup/verify", json={"challenge_id": ch["challenge_id"], "code": ch["dev_code"]})
    assert r.status_code == 429 and r.json()["error"]["code"] == "otp_locked"


def test_resend_cooldown(client, db):
    make_subscriber(db)
    db.commit()
    assert _start(client).status_code == 200
    r = _start(client)
    assert r.status_code == 429 and r.json()["error"]["code"] == "otp_cooldown"
    assert 1 <= int(r.headers["retry-after"]) <= 61


def test_otp_expiry(client, db):
    from app.core import clock

    make_subscriber(db)
    db.commit()
    ch = _start(client).json()
    clock.advance(seconds=121)
    r = client.post("/api/v1/app/auth/signup/verify", json={"challenge_id": ch["challenge_id"], "code": ch["dev_code"]})
    assert r.json()["error"]["code"] == "otp_expired"


def test_otp_rate_limit_per_mobile(client, db):
    from app.core import clock

    make_subscriber(db)
    db.commit()
    for _ in range(3):
        assert _start(client).status_code == 200
        clock.advance(seconds=61)
    r = _start(client)
    assert r.status_code == 429 and r.json()["error"]["code"] == "rate_limited"


def test_terms_required_and_password_rules(client, db):
    make_subscriber(db)
    db.commit()
    ch = _start(client).json()
    tok = client.post("/api/v1/app/auth/signup/verify", json={"challenge_id": ch["challenge_id"], "code": ch["dev_code"]}).json()["signup_token"]
    r = client.post("/api/v1/app/auth/signup/complete", json={"signup_token": tok, "accept_terms": False, "accept_privacy": True})
    assert r.json()["error"]["code"] == "terms_required"
    r = client.post("/api/v1/app/auth/signup/complete", json={"signup_token": tok, "accept_terms": True, "accept_privacy": True,
                                                              "login_method": "password", "password": "short"})
    assert r.status_code == 422
    r = client.post("/api/v1/app/auth/signup/complete", json={"signup_token": tok, "accept_terms": True, "accept_privacy": True,
                                                              "login_method": "password", "password": PASSWORD})
    assert r.status_code == 200
    r = client.post("/api/v1/app/auth/login/password", json={"mobile": "09121112233", "password": PASSWORD})
    assert r.status_code == 200 and r.json()["subject_type"] == "user"


def test_login_otp_unknown_number_gets_decoy(client, db):
    make_user(db)
    db.commit()
    known = client.post("/api/v1/app/auth/login/otp/start", json={"mobile": "09121112233"})
    unknown = client.post("/api/v1/app/auth/login/otp/start", json={"mobile": "09129999999"})
    assert known.status_code == unknown.status_code == 200
    assert set(known.json()) - {"dev_code"} == set(unknown.json()) - {"dev_code"}
    # The decoy can never be verified, whatever the code
    for code in ("12345", "00000"):
        r = client.post("/api/v1/app/auth/login/otp/verify", json={"challenge_id": unknown.json()["challenge_id"], "code": code})
        assert r.json()["error"]["code"] == "otp_wrong"
    ok = client.post("/api/v1/app/auth/login/otp/verify", json={"challenge_id": known.json()["challenge_id"], "code": known.json()["dev_code"]})
    assert ok.status_code == 200


def test_refresh_rotation_and_reuse_detection(client, db):
    make_user(db)
    db.commit()
    ch = client.post("/api/v1/app/auth/login/otp/start", json={"mobile": "09121112233"}).json()
    r = client.post("/api/v1/app/auth/login/otp/verify", json={"challenge_id": ch["challenge_id"], "code": ch["dev_code"]},
                    headers={"X-Client": "native"})
    rt1 = r.json()["refresh_token"]
    assert rt1
    r2 = client.post("/api/v1/auth/refresh", json={"refresh_token": rt1}, headers={"X-Client": "native"})
    assert r2.status_code == 200
    rt2 = r2.json()["refresh_token"]
    # Reusing the rotated token kills the whole family, including rt2
    assert client.post("/api/v1/auth/refresh", json={"refresh_token": rt1}, headers={"X-Client": "native"}).status_code == 401
    assert client.post("/api/v1/auth/refresh", json={"refresh_token": rt2}, headers={"X-Client": "native"}).status_code == 401


def test_web_refresh_uses_httponly_cookie(client, db):
    make_user(db)
    db.commit()
    ch = client.post("/api/v1/app/auth/login/otp/start", json={"mobile": "09121112233"}).json()
    r = client.post("/api/v1/app/auth/login/otp/verify", json={"challenge_id": ch["challenge_id"], "code": ch["dev_code"]})
    assert r.json()["refresh_token"] is None
    cookie = r.headers["set-cookie"]
    assert "gz_rt=" in cookie and "HttpOnly" in cookie and "samesite=strict" in cookie.lower() and "Path=/api/v1/auth" in cookie
    assert client.post("/api/v1/auth/refresh").status_code == 200  # TestClient replays the cookie


def test_suspended_user_blocked(client, db):
    from tests.conftest import user_headers

    u = make_user(db)
    u.status = "suspended"
    db.commit()
    r = client.get("/api/v1/app/me", headers=user_headers(u))
    assert r.status_code == 403 and r.json()["error"]["code"] == "account_suspended"


def test_referral_recorded_not_paid_at_signup(client, db):
    from sqlalchemy import select

    from app.modules.referrals.models import Referral

    referrer = make_user(db, sn="5555555555", mobile="09125555555")
    referrer.referral_code = "ABC2345"
    make_subscriber(db)
    db.commit()
    _full_signup(client, db, referral_code="abc2345")
    ref = db.scalar(select(Referral))
    assert ref is not None and ref.status == "pending"
    from app.modules.points.service import balance

    assert balance(db, referrer.id).total == 0  # R24: entering a code alone pays nothing
