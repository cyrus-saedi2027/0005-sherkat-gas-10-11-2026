from datetime import UTC, date, datetime

import pytest

from app.core import crypto, jalali, ratelimit, security
from app.core import settings_registry as reg
from app.core.errors import AppError
from app.core.rbac import ROLE_PERMISSIONS, P, Role, permissions_for
from app.core.validators import is_valid_national_code, password_problem


def test_jalali_period_and_month_boundaries():
    # 2026-10-12 08:30 UTC = 1405-07-20 in Tehran
    assert jalali.period_key(datetime(2026, 10, 12, 8, 30, tzinfo=UTC)) == "1405-07"
    # 20:45 UTC on the last day of Shahrivar is already Mehr 1st in Tehran (+03:30)
    assert jalali.period_key(datetime(2026, 9, 22, 20, 45, tzinfo=UTC)) == "1405-07"
    assert jalali.period_key(datetime(2026, 9, 22, 20, 15, tzinfo=UTC)) == "1405-06"
    assert jalali.next_month_start_utc(datetime(2026, 10, 12, tzinfo=UTC)) == datetime(2026, 10, 22, 20, 30, tzinfo=UTC)
    assert jalali.shift_period("1405-12", 1) == "1406-01"
    assert jalali.shift_period("1405-01", -1) == "1404-12"
    assert jalali.period_key(date(2026, 10, 12), 2) == "1405-07"
    assert jalali.period_key(date(2026, 11, 10), 2) == "1405-07"  # Aban pairs with Mehr
    assert jalali.period_label("1405-07") == "مهر ۱۴۰۵"
    assert jalali.days_in_period("1405-01") == 31 and jalali.days_in_period("1405-07") == 30


def test_crypto_roundtrip_and_blind_index():
    t = crypto.encrypt("09121234567")
    assert t != "09121234567" and crypto.decrypt(t) == "09121234567"
    assert crypto.blind_index("x", purpose="mobile") == crypto.blind_index("x", purpose="mobile")
    assert crypto.blind_index("x", purpose="mobile") != crypto.blind_index("x", purpose="national_code")


def test_password_hash_and_timing_dummy():
    h = security.hash_password("Abcdefg1")
    assert security.verify_password("Abcdefg1", h)
    assert not security.verify_password("wrong123", h)
    assert not security.verify_password("anything1", None)  # dummy hash path, never True
    assert password_problem("short1") and password_problem("onlyletters") and password_problem("12345678")
    assert password_problem("goodpass1") is None


def test_tokens_respect_frozen_clock():
    from app.core import clock

    tok = security.issue_access_token("user", 7)
    assert security.decode_token(tok, "access")["sub"] == "7"
    clock.advance(minutes=16)
    import jwt

    with pytest.raises(jwt.ExpiredSignatureError):
        security.decode_token(tok, "access")


def test_wrong_token_type_rejected():
    import jwt

    tok = security.issue_purpose_token("signup", {"sid": 1}, 5)
    with pytest.raises(jwt.InvalidTokenError):
        security.decode_token(tok, "access")


def test_rbac_business_rules():
    # R34: operators can never touch finance settings or delete data
    assert P.SETTINGS_FINANCE_EDIT not in ROLE_PERMISSIONS[Role.OPERATOR]
    assert P.DATA_DELETE not in ROLE_PERMISSIONS[Role.OPERATOR]
    assert ROLE_PERMISSIONS[Role.SUPER_ADMIN] == frozenset(P)
    assert P.CASES_WORK in permissions_for(["ambassador"]) and P.CASES_VIEW_ALL not in permissions_for(["ambassador"])
    assert permissions_for(["bogus"]) == frozenset()
    assert P.REDEMPTIONS_REVIEW in permissions_for(["finance"])


def test_ratelimit_window():
    for _ in range(3):
        ratelimit.enforce("k", 3, 60)
    with pytest.raises(AppError) as e:
        ratelimit.enforce("k", 3, 60)
    assert e.value.status == 429 and e.value.details["retry_after"] >= 1


def test_settings_coercion():
    spec = reg.BY_KEY["eligibility.threshold_m3"]
    assert reg.coerce(spec, "4000") == 4000
    with pytest.raises(ValueError):
        reg.coerce(spec, -1)
    with pytest.raises(ValueError):
        reg.coerce(spec, "abc")
    with pytest.raises(ValueError):
        reg.coerce(reg.BY_KEY["eligibility.threshold_basis"], "weekly")
    assert reg.coerce(reg.BY_KEY["reading.period_months"], "2") == 2


def test_national_code_known_values():
    assert is_valid_national_code("0499370899")
    assert is_valid_national_code("۰۴۹۹۳۷۰۸۹۹")
    assert not is_valid_national_code("1111111111")
    assert not is_valid_national_code("0499370898")
