"""Feature flag for repo / PR / MR workflow overlays (Sprint 3)."""

from __future__ import annotations

import os


def experimental_repo_workflow_enabled() -> bool:
    """On by default (local fixtures + graph links; remote adapters optional).

    Set ``LENSES_EXPERIMENTAL_REPO_WORKFLOW=0`` (or ``false`` / ``no`` / ``off``) to hide APIs and UI data.
    """
    raw = (os.environ.get("LENSES_EXPERIMENTAL_REPO_WORKFLOW") or "").strip().lower()
    if raw in ("0", "false", "no", "off"):
        return False
    if not raw:
        return True
    return raw in ("1", "true", "yes", "on")
