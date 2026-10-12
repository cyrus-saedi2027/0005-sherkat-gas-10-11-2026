"""Checksum validators shared in spirit with packages/core (same fixtures)."""

from __future__ import annotations

import re

from app.core.normalize import to_ascii_digits


def is_valid_national_code(s: str | None) -> bool:
    if not s:
        return False
    t = re.sub(r"[\s\-]", "", to_ascii_digits(s))
    if not re.fullmatch(r"[0-9]{10}", t) or len(set(t)) == 1:
        return False
    total = sum(int(t[i]) * (10 - i) for i in range(9))
    r = total % 11
    check = int(t[9])
    return check == r if r < 2 else check == 11 - r


def normalize_iban(s: str | None) -> str | None:
    if not s:
        return None
    t = re.sub(r"[\s\-]", "", to_ascii_digits(s)).upper()
    if re.fullmatch(r"[0-9]{24}", t):
        t = "IR" + t
    return t if re.fullmatch(r"IR[0-9]{24}", t) else None


def is_valid_iban(s: str | None) -> bool:
    t = normalize_iban(s)
    if not t:
        return False
    moved = t[4:] + t[:4]
    digits = "".join(str(int(ch, 36)) for ch in moved)
    rem = 0
    for i in range(0, len(digits), 9):
        rem = int(str(rem) + digits[i : i + 9]) % 97
    return rem == 1


def password_problem(pw: str) -> str | None:
    """Persian reason the password is unacceptable, or None."""
    if len(pw) < 8:
        return "رمز عبور باید دست‌کم ۸ نویسه باشد."
    if len(pw) > 128:
        return "رمز عبور بیش از حد طولانی است."
    # str.isalpha() is True for Persian/Arabic letters and False for every digit set — same rule as
    # packages/core (\p{L}); a Unicode block range would wrongly count ۰-۹ as letters.
    if not any(ch.isalpha() for ch in pw) or not re.search(r"[0-9]", to_ascii_digits(pw)):
        return "رمز عبور باید هم حرف و هم عدد داشته باشد."
    return None
