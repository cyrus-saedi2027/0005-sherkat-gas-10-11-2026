"""SMS providers + outbox worker. `console` logs instead of sending (dev/test)."""

from __future__ import annotations

import logging
from typing import Protocol

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core import clock, crypto
from app.core.config import get_settings

log = logging.getLogger("gazyar.sms")

# Dev/test only: last OTP text per mobile, so E2E tests can read codes without a phone.
DEV_LAST: dict[str, str] = {}


class SmsProvider(Protocol):
    def send(self, mobile: str, text: str) -> str: ...


class ConsoleProvider:
    def send(self, mobile: str, text: str) -> str:
        DEV_LAST[mobile] = text
        log.info("SMS to %s: %s", mobile, text)
        return "console"


class KavenegarProvider:
    def __init__(self, api_key: str, sender: str) -> None:
        self.api_key, self.sender = api_key, sender

    def send(self, mobile: str, text: str) -> str:
        url = f"https://api.kavenegar.com/v1/{self.api_key}/sms/send.json"
        r = httpx.post(url, data={"receptor": mobile, "message": text, "sender": self.sender}, timeout=10)
        r.raise_for_status()
        entries = r.json().get("entries") or [{}]
        return str(entries[0].get("messageid", ""))


def provider() -> SmsProvider:
    s = get_settings()
    if s.sms_provider == "kavenegar":
        return KavenegarProvider(s.sms_api_key, s.sms_sender)
    return ConsoleProvider()


def queue(db: Session, mobile: str, text: str, purpose: str, sensitive: bool = False) -> None:
    from app.modules.notifications.models import SmsOutbox

    db.add(SmsOutbox(mobile_enc=crypto.encrypt(mobile) or "", text=text, purpose=purpose, sensitive=sensitive))


def drain(db: Session, batch: int = 50) -> int:
    """Send queued messages. Safe to call from a scheduler or after a request."""
    from app.modules.notifications.models import SmsOutbox

    rows = db.scalars(
        select(SmsOutbox).where(SmsOutbox.status == "queued").order_by(SmsOutbox.id).limit(batch).with_for_update(skip_locked=True)
    ).all()
    p = provider()
    sent = 0
    for m in rows:
        m.attempts += 1
        try:
            m.provider_ref = p.send(crypto.decrypt(m.mobile_enc) or "", m.text)
            m.status, m.sent_at = "sent", clock.now()
            sent += 1
        except Exception as e:  # provider down → retry later, give up after 5
            m.error = str(e)[:300]
            if m.attempts >= 5:
                m.status = "failed"
        if m.sensitive and m.status != "queued":
            m.text = "[redacted]"
    db.flush()
    return sent
