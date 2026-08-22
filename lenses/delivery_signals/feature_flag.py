"""Feature flag for delivery / pipeline signal overlays (fixtures and future remote adapters)."""

from __future__ import annotations

import os


def experimental_delivery_signals_enabled() -> bool:
    """On by default (local scan + optional JSON only — no outbound network).

    Set ``LENSES_EXPERIMENTAL_DELIVERY_SIGNALS=0`` (or ``false`` / ``no`` / ``off``) to hide overlays
    and return a disabled-shaped API payload for Studio.
    """
    raw = (os.environ.get("LENSES_EXPERIMENTAL_DELIVERY_SIGNALS") or "").strip().lower()
    if raw in ("0", "false", "no", "off"):
        return False
    if not raw:
        return True
    return raw in ("1", "true", "yes", "on")
