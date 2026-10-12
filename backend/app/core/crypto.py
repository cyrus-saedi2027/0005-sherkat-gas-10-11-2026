"""Field-level encryption for sensitive data (R35) + blind indexes for exact-match search.

Mobile numbers, national codes and IBANs are stored encrypted (MultiFernet so
keys can rotate). Exact lookups ("find by mobile") use an HMAC blind index of
the *normalised* value — never the plaintext.
"""

from __future__ import annotations

import hashlib
import hmac
from functools import lru_cache

from cryptography.fernet import Fernet, InvalidToken, MultiFernet

from app.core.config import get_settings


@lru_cache
def _fernet() -> MultiFernet:
    keys = [k.strip() for k in get_settings().fernet_keys.split(",") if k.strip()]
    if not keys:
        raise RuntimeError("GAZYAR_FERNET_KEYS is empty")
    return MultiFernet([Fernet(k.encode()) for k in keys])


def encrypt(value: str | None) -> str | None:
    if value is None:
        return None
    return _fernet().encrypt(value.encode()).decode()


def decrypt(token: str | None) -> str | None:
    if token is None:
        return None
    try:
        return _fernet().decrypt(token.encode()).decode()
    except InvalidToken as e:  # wrong key set — fail loudly, never return garbage
        raise RuntimeError("cannot decrypt field: key mismatch") from e


def rotate(token: str) -> str:
    """Re-encrypt with the newest key (used by a maintenance command after adding a key)."""
    return _fernet().rotate(token.encode()).decode()


def blind_index(value: str | None, *, purpose: str = "default") -> str | None:
    """Deterministic HMAC of a normalised value. `purpose` separates domains (mobile vs national code)."""
    if value is None:
        return None
    key = get_settings().blind_index_key.encode()
    return hmac.new(key, f"{purpose}:{value}".encode(), hashlib.sha256).hexdigest()


def hmac_hex(key: str, msg: str) -> str:
    return hmac.new(key.encode(), msg.encode(), hashlib.sha256).hexdigest()


def safe_equals(a: str, b: str) -> bool:
    return hmac.compare_digest(a.encode(), b.encode())


def reset_caches() -> None:
    _fernet.cache_clear()
