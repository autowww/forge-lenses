"""Feature flag for ops feedback loop and delivery metrics (Sprint 8)."""

from __future__ import annotations

import os


def experimental_ops_delivery_enabled() -> bool:
    """On by default. Set ``LENSES_EXPERIMENTAL_OPS_DELIVERY=0`` to disable."""
    raw = (os.environ.get("LENSES_EXPERIMENTAL_OPS_DELIVERY") or "").strip().lower()
    if raw in ("0", "false", "no", "off"):
        return False
    if not raw:
        return True
    return raw in ("1", "true", "yes", "on")
