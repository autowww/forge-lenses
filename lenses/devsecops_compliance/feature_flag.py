"""Feature flag for DevSecOps / compliance orchestration (Sprint 6)."""

from __future__ import annotations

import os


def experimental_devsecops_compliance_enabled() -> bool:
    """On by default. Set ``LENSES_EXPERIMENTAL_DEVSECOPS_COMPLIANCE=0`` to disable."""
    raw = (os.environ.get("LENSES_EXPERIMENTAL_DEVSECOPS_COMPLIANCE") or "").strip().lower()
    if raw in ("0", "false", "no", "off"):
        return False
    if not raw:
        return True
    return raw in ("1", "true", "yes", "on")
