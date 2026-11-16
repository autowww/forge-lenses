"""Feature flag for Foundry UI and API."""

from __future__ import annotations

import os

from lenses.bridge.agentic_b3_feature_flag import experimental_agentic_bridge_b3_enabled


def foundry_enabled() -> bool:
    """On when agentic B3 bridge is on unless ``LENSES_EXPERIMENTAL_FOUNDRY=0``."""
    if not experimental_agentic_bridge_b3_enabled():
        return False
    raw = (os.environ.get("LENSES_EXPERIMENTAL_FOUNDRY") or "").strip().lower()
    if raw in ("0", "false", "no", "off"):
        return False
    return True
