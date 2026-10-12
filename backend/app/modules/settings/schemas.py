from __future__ import annotations

from typing import Any

from pydantic import BaseModel


class SettingOut(BaseModel):
    key: str
    value: Any
    default: Any
    kind: str
    category: str
    category_fa: str
    title_fa: str
    help_fa: str
    unit_fa: str
    min: float | None
    max: float | None
    choices: list[dict[str, str]]
    editable: bool


class SettingsUpdate(BaseModel):
    values: dict[str, Any]
