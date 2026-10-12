"""Password hashing and JWT tokens."""

from __future__ import annotations

import hashlib
import secrets
import uuid
from datetime import timedelta
from typing import Any, Literal

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError

from app.core import clock
from app.core.config import get_settings

_ph = PasswordHasher()  # argon2id with library defaults (memory-hard)

# A real argon2 hash used to burn the same CPU when the account does not exist,
# so login timing does not reveal which usernames/mobiles are registered.
_DUMMY_HASH = _ph.hash("dummy-password-for-timing-equalisation")

ALGO = "HS256"
SubjectType = Literal["user", "staff"]


def hash_password(pw: str) -> str:
    return _ph.hash(pw)


def verify_password(pw: str, hashed: str | None) -> bool:
    try:
        return _ph.verify(hashed or _DUMMY_HASH, pw) and hashed is not None
    except (VerifyMismatchError, VerificationError, InvalidHashError):
        return False


def needs_rehash(hashed: str) -> bool:
    return _ph.check_needs_rehash(hashed)


def _encode(claims: dict[str, Any], ttl: timedelta) -> str:
    now = clock.now()
    payload = {**claims, "iat": int(now.timestamp()), "exp": int((now + ttl).timestamp()), "jti": uuid.uuid4().hex}
    return jwt.encode(payload, get_settings().secret_key, algorithm=ALGO)


def issue_access_token(subject_type: SubjectType, subject_id: int, extra: dict[str, Any] | None = None) -> str:
    s = get_settings()
    return _encode({"sub": str(subject_id), "typ": "access", "st": subject_type, **(extra or {})}, timedelta(minutes=s.access_token_minutes))


def issue_purpose_token(purpose: str, claims: dict[str, Any], minutes: int) -> str:
    """Short-lived single-purpose token (e.g. signup completion after OTP)."""
    return _encode({"typ": purpose, **claims}, timedelta(minutes=minutes))


def decode_token(token: str, expected_type: str) -> dict[str, Any]:
    """Raises jwt.ExpiredSignatureError / jwt.InvalidTokenError."""
    # PyJWT checks exp/iat against the wall clock; we verify against clock.now()
    # instead so frozen-time tests (month-end boundaries) behave like production.
    payload = jwt.decode(
        token,
        get_settings().secret_key,
        algorithms=[ALGO],
        options={"require": ["exp", "iat", "typ"], "verify_exp": False, "verify_iat": False},
    )
    if int(payload["exp"]) <= int(clock.now().timestamp()):
        raise jwt.ExpiredSignatureError("token expired")
    if payload.get("typ") != expected_type:
        raise jwt.InvalidTokenError("wrong token type")
    return payload


def new_refresh_token() -> tuple[str, str]:
    """(plaintext, sha256) — only the hash is stored."""
    raw = secrets.token_urlsafe(48)
    return raw, hashlib.sha256(raw.encode()).hexdigest()


def sha256_hex(s: str) -> str:
    return hashlib.sha256(s.encode()).hexdigest()


def random_otp(digits: int = 5) -> str:
    return "".join(secrets.choice("0123456789") for _ in range(digits))
