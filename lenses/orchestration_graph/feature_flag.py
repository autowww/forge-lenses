"""Feature flag for the canonical orchestration graph (SQLite under ``.lenses-local/``)."""

from __future__ import annotations

import os


def experimental_orchestration_graph_enabled() -> bool:
    """On by default. Set ``LENSES_EXPERIMENTAL_ORCHESTRATION_GRAPH=0`` / ``false`` / ``no`` / ``off`` to disable."""
    raw = (os.environ.get("LENSES_EXPERIMENTAL_ORCHESTRATION_GRAPH") or "").strip().lower()
    if raw in ("0", "false", "no", "off"):
        return False
    if not raw:
        return True
    return raw in ("1", "true", "yes", "on")


def orchestration_auto_seed_enabled() -> bool:
    """When the graph DB is empty, load the bundled demo fixture (unless disabled)."""
    raw = (os.environ.get("LENSES_ORCHESTRATION_AUTO_SEED") or "").strip().lower()
    if raw in ("0", "false", "no", "off"):
        return False
    if not raw:
        return True
    return raw in ("1", "true", "yes", "on")
