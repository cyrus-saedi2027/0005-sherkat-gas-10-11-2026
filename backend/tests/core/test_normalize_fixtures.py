"""The shared fixture is the contract between packages/core (TS) and the backend (R07)."""

import json
from pathlib import Path

import pytest

from app.core.normalize import normalize_mobile, normalize_subscription, normalize_text, to_ascii_digits
from app.core.validators import is_valid_iban, is_valid_national_code, normalize_iban

FIXTURE = Path(__file__).resolve().parents[3] / "packages" / "core" / "fixtures" / "normalize.json"
DATA = json.loads(FIXTURE.read_text(encoding="utf-8")) if FIXTURE.exists() else {}


@pytest.mark.skipif(not DATA, reason="shared fixture missing")
@pytest.mark.parametrize("case", DATA.get("digits", []))
def test_digits(case):
    assert to_ascii_digits(case["in"]) == case["out"]


@pytest.mark.parametrize("case", DATA.get("text", []))
def test_text(case):
    assert normalize_text(case["in"]) == case["out"]


@pytest.mark.parametrize("case", DATA.get("mobile", []))
def test_mobile(case):
    assert normalize_mobile(case["in"]) == case["out"]


@pytest.mark.parametrize("case", DATA.get("subscription", []))
def test_subscription(case):
    assert normalize_subscription(case["in"]) == case["out"]


@pytest.mark.parametrize("case", DATA.get("national_code", []))
def test_national_code(case):
    assert is_valid_national_code(case["in"]) is case["valid"]


@pytest.mark.parametrize("case", DATA.get("iban", []))
def test_iban(case):
    assert normalize_iban(case["in"]) == case["out"]
    assert is_valid_iban(case["in"]) is case["valid"]
