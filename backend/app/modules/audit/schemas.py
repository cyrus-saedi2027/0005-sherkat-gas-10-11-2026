from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel


class AuditOut(BaseModel):
    id: int
    actor_type: str
    actor_id: int | None
    actor_name: str | None = None
    action: str
    entity_type: str
    entity_id: str | None
    before: dict[str, Any] | None
    after: dict[str, Any] | None
    ip: str | None
    created_at: datetime


class LoginEventOut(BaseModel):
    id: int
    actor_type: str
    actor_id: int | None
    identifier_masked: str
    success: bool
    reason: str
    ip: str | None
    user_agent: str | None
    created_at: datetime
