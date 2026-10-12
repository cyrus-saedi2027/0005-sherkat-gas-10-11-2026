from __future__ import annotations

from typing import Any

from fastapi import Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core import audit
from app.core import settings_registry as reg
from app.core.errors import AppError
from app.core.rbac import P
from app.modules.settings.models import Setting
from app.modules.settings.schemas import SettingOut


def list_settings(db: Session, perms: frozenset[P]) -> list[SettingOut]:
    stored = {s.key: s.value for s in db.scalars(select(Setting)).all()}
    return [
        SettingOut(
            key=s.key, value=stored.get(s.key, s.default), default=s.default, kind=s.kind, category=s.category,
            category_fa=reg.CATEGORY_FA.get(s.category, s.category), title_fa=s.title_fa, help_fa=s.help_fa,
            unit_fa=s.unit_fa, min=s.min, max=s.max, choices=[{"value": c, "label": lbl} for c, lbl in s.choices],
            editable=s.permission in perms,
        )
        for s in reg.SPECS
    ]


def update_settings(db: Session, values: dict[str, Any], actor: audit.Actor, perms: frozenset[P],
                    request: Request | None = None) -> None:
    errors: dict[str, str] = {}
    coerced: dict[str, Any] = {}
    for key, raw in values.items():
        spec = reg.BY_KEY.get(key)
        if spec is None:
            errors[key] = "تنظیم ناشناخته است."
            continue
        if spec.permission not in perms:
            # R34: e.g. an operator touching finance settings → refuse the whole request.
            raise AppError("forbidden", f"شما اجازهٔ تغییر «{spec.title_fa}» را ندارید.", 403, {"key": key})
        try:
            coerced[key] = reg.coerce(spec, raw)
        except ValueError as e:
            errors[key] = str(e)
    if errors:
        raise AppError("validation_error", "برخی مقادیر معتبر نیستند.", 422, {"fields": errors})
    for key, val in coerced.items():
        row = db.scalar(select(Setting).where(Setting.key == key))
        before = row.value if row else reg.BY_KEY[key].default
        if before == val:
            continue
        if row is None:
            db.add(Setting(key=key, value=val, updated_by=actor.id))
        else:
            row.value = val
            row.updated_by = actor.id
        audit.record(db, actor, "settings.update", "setting", key, {"value": before}, {"value": val}, request)
    db.flush()
    reg.invalidate(db)
