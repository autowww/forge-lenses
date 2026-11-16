"""Feature flag for test management and quality gates (Sprint 5)."""

from __future__ import annotations

import os


def experimental_test_quality_enabled() -> bool:
    """On by default. Set ``LENSES_EXPERIMENTAL_TEST_QUALITY=0`` to disable."""
    raw = (os.environ.get("LENSES_EXPERIMENTAL_TEST_QUALITY") or "").strip().lower()
    if raw in ("0", "false", "no", "off"):
        return False
    if not raw:
        return True
    return raw in ("1", "true", "yes", "on")
