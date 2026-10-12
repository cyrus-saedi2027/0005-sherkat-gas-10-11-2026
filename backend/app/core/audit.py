"""audit.record(...) — call inside the same transaction as the change it describes."""

from __future__ import annotations

import dataclasses
from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from typing import Any

from fastapi import Request
from sqlalchemy.orm import Session

# Never written into the audit trail even if a caller passes a whole row dict.
_REDACT = {"password_hash", "code_hash", "token_hash", "mobile_enc", "national_code_enc", "iban_enc", "password"}


@dataclasses.dataclass(frozen=True)
class Actor:
    type: str  # staff | user | system
    id: int | None
    roles: tuple[str, ...] = ()


SYSTEM = Actor("system", None)


def _clean(v: Any) -> Any:
    if isinstance(v, dict):
        return {k: ("***" if k in _REDACT else _clean(x)) for k, x in v.items()}
    if isinstance(v, list | tuple | set):
        return [_clean(x) for x in v]
    if isinstance(v, datetime | date):
        return v.isoformat()
    if isinstance(v, Decimal):
        return float(v)
    if isinstance(v, Enum):
        return v.value
    return v


def record(
    db: Session,
    actor: Actor,
    action: str,
    entity_type: str,
    entity_id: Any = None,
    before: dict[str, Any] | None = None,
    after: dict[str, Any] | None = None,
    request: Request | None = None,
) -> None:
    from app.modules.audit.models import AuditLog

    ip = ua = rid = None
    if request is not None:
        ip = client_ip(request)
        ua = (request.headers.get("user-agent") or "")[:300]
        rid = getattr(request.state, "request_id", None)
    db.add(
        AuditLog(
            actor_type=actor.type,
            actor_id=actor.id,
            action=action,
            entity_type=entity_type,
            entity_id=None if entity_id is None else str(entity_id),
            before=_clean(before) if before is not None else None,
            after=_clean(after) if after is not None else None,
            ip=ip,
            user_agent=ua,
            request_id=rid,
        )
    )


def login_event(db: Session, *, actor_type: str, actor_id: int | None, identifier_masked: str,
                success: bool, reason: str, request: Request | None) -> None:
    from app.modules.audit.models import LoginEvent

    db.add(LoginEvent(
        actor_type=actor_type, actor_id=actor_id, identifier_masked=identifier_masked, success=success,
        reason=reason, ip=client_ip(request) if request else None,
        user_agent=(request.headers.get("user-agent") or "")[:300] if request else None,
    ))


def client_ip(request: Request) -> str:
    # Behind nginx we trust X-Real-IP set by our own proxy (DEPLOYMENT.md); never X-Forwarded-For blindly.
    return request.headers.get("x-real-ip") or (request.client.host if request.client else "unknown")


def snapshot(obj: Any, fields: list[str]) -> dict[str, Any]:
    return {f: getattr(obj, f, None) for f in fields}
