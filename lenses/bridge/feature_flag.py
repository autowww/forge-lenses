"""Feature flag: methodology bridge spine (registry + trace projections)."""

from __future__ import annotations

import os

from lenses.orchestration_graph.feature_flag import experimental_orchestration_graph_enabled


def experimental_bridge_spine_enabled() -> bool:
    """On by default when orchestration graph is on. Set ``LENSES_EXPERIMENTAL_BRIDGE_SPINE=0`` to disable."""
    if not experimental_orchestration_graph_enabled():
        return False
    raw = (os.environ.get("LENSES_EXPERIMENTAL_BRIDGE_SPINE") or "").strip().lower()
    if raw in ("0", "false", "no", "off"):
        return False
    if not raw:
        return True
    return raw in ("1", "true", "yes", "on")
