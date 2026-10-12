"""Local file storage + HMAC-signed, short-lived URLs (files are never public)."""

from __future__ import annotations

import hashlib
import hmac
from pathlib import Path

from app.core import clock
from app.core.config import get_settings


def _root() -> Path:
    root = get_settings().upload_dir
    root.mkdir(parents=True, exist_ok=True)
    return root


def save(key: str, data: bytes) -> None:
    path = _root() / key
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_bytes(data)
    tmp.replace(path)


def read(key: str) -> bytes:
    path = (_root() / key).resolve()
    if _root().resolve() not in path.parents:
        raise FileNotFoundError(key)  # path traversal guard
    return path.read_bytes()


def path_of(key: str) -> Path:
    path = (_root() / key).resolve()
    if _root().resolve() not in path.parents:
        raise FileNotFoundError(key)
    return path


def _sig(file_id: str, variant: str, exp: int) -> str:
    msg = f"{file_id}:{variant}:{exp}".encode()
    return hmac.new(get_settings().secret_key.encode(), msg, hashlib.sha256).hexdigest()[:32]


def signed_url(file_id: str | None, variant: str = "full", ttl: int | None = None) -> str | None:
    if not file_id:
        return None
    exp = int(clock.now().timestamp()) + (ttl or get_settings().file_url_ttl_seconds)
    # Round expiry up to the minute so URLs are cache-friendly within a minute.
    exp = exp - exp % 60 + 60
    return f"/api/v1/files/{file_id}?v={variant}&exp={exp}&sig={_sig(file_id, variant, exp)}"


def verify(file_id: str, variant: str, exp: int, sig: str) -> bool:
    if exp < int(clock.now().timestamp()):
        return False
    return hmac.compare_digest(_sig(file_id, variant, exp), sig)
