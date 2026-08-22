"""Feature flag for cross-team dependency and change orchestration (Sprint 7)."""

from __future__ import annotations

import os


def experimental_cross_team_release_enabled() -> bool:
    """On by default. Set ``LENSES_EXPERIMENTAL_CROSS_TEAM_RELEASE=0`` to disable."""
    raw = (os.environ.get("LENSES_EXPERIMENTAL_CROSS_TEAM_RELEASE") or "").strip().lower()
    if raw in ("0", "false", "no", "off"):
        return False
    if not raw:
        return True
    return raw in ("1", "true", "yes", "on")
