"""Input normalisation — MUST stay byte-for-byte equivalent to packages/core/src/i18n/normalize.ts.

The shared fixture packages/core/fixtures/normalize.json is loaded by tests on
both sides. If these drift, a subscriber typed on an Arabic keyboard becomes
unmatchable on one side and nobody can see why (the strings look identical).
"""

from __future__ import annotations

import re

_DIGITS = str.maketrans("۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩", "01234567890123456789")
_CHARS = str.maketrans({"ي": "ی", "ى": "ی", "ك": "ک", "ة": "ه"})
_DIACRITICS = re.compile("[ً-ْٰـ]")
_WS = re.compile(r"\s+")
_MOBILE_JUNK = re.compile(r"[\s\-()]")
_SUB_JUNK = re.compile(r"[\s\-/.]")


def to_ascii_digits(s: str) -> str:
    return s.translate(_DIGITS)


def normalize_text(s: str) -> str:
    s = to_ascii_digits(s).translate(_CHARS)
    s = _DIACRITICS.sub("", s)
    s = s.replace("‌", " ")
    s = _WS.sub(" ", s).strip()
    # Only Latin letters are lower-cased (Persian has no case; str.lower() is safe for it anyway).
    return "".join(ch.lower() if "A" <= ch <= "Z" else ch for ch in s)


def normalize_mobile(s: str | None) -> str | None:
    if not s:
        return None
    t = _MOBILE_JUNK.sub("", to_ascii_digits(s))
    for prefix in ("+98", "0098", "98", "0"):
        if t.startswith(prefix) and len(t) - len(prefix) == 10:
            t = t[len(prefix):]
            break
    return "0" + t if re.fullmatch(r"9\d{9}", t) else None


def normalize_subscription(s: str | None) -> str | None:
    if s is None:
        return None
    t = _SUB_JUNK.sub("", to_ascii_digits(str(s)))
    return t if re.fullmatch(r"\d{4,20}", t) else None


def mask_mobile(m: str | None) -> str:
    if not m or len(m) < 8:
        return "—"
    return f"{m[:4]}***{m[-4:]}"
