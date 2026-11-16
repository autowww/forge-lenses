"""Feature flag for CI/CD control tower (Sprint 4)."""

from __future__ import annotations

import os


def experimental_cicd_orchestration_enabled() -> bool:
    """On by default. Set ``LENSES_EXPERIMENTAL_CICD_ORCHESTRATION=0`` to disable APIs and UI data."""
    raw = (os.environ.get("LENSES_EXPERIMENTAL_CICD_ORCHESTRATION") or "").strip().lower()
    if raw in ("0", "false", "no", "off"):
        return False
    if not raw:
        return True
    return raw in ("1", "true", "yes", "on")
