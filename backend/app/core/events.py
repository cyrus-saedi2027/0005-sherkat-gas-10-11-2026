"""In-process domain events so modules stay decoupled.

readings emits "reading.approved"; stage-2 modules (cases, referrals) subscribe
without readings importing them. Handlers run synchronously inside the same
transaction — if a handler fails, the whole approval rolls back (no half state).
"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Callable
from typing import Any

Handler = Callable[..., None]
_handlers: dict[str, list[Handler]] = defaultdict(list)


def on(event: str) -> Callable[[Handler], Handler]:
    def deco(fn: Handler) -> Handler:
        if fn not in _handlers[event]:
            _handlers[event].append(fn)
        return fn

    return deco


def emit(event: str, **kwargs: Any) -> None:
    for fn in list(_handlers[event]):
        fn(**kwargs)
