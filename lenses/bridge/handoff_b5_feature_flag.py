"""Sprint B5: Cursor / Claude handoff and execution-return loop."""

from __future__ import annotations

import os

from lenses.orchestration_graph.feature_flag import experimental_orchestration_graph_enabled


def experimental_handoff_bridge_b5_enabled() -> bool:
    """On when orchestration graph is on. Set ``LENSES_EXPERIMENTAL_HANDOFF_BRIDGE_B5=0`` to disable."""
    if not experimental_orchestration_graph_enabled():
        return False
    raw = (os.environ.get("LENSES_EXPERIMENTAL_HANDOFF_BRIDGE_B5") or "").strip().lower()
    if raw in ("0", "false", "no", "off"):
        return False
    if not raw:
        return True
    return raw in ("1", "true", "yes", "on")
