"""Feature flag for grounded SDLC copilot (Sprint 9)."""

from __future__ import annotations

import os


def experimental_sdlc_copilot_enabled() -> bool:
    """On by default. Set ``LENSES_EXPERIMENTAL_SDLC_COPILOT=0`` to disable."""
    raw = (os.environ.get("LENSES_EXPERIMENTAL_SDLC_COPILOT") or "").strip().lower()
    if raw in ("0", "false", "no", "off"):
        return False
    if not raw:
        return True
    return raw in ("1", "true", "yes", "on")
