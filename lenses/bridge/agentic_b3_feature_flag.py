"""Sprint B3: agentic bridge (Versonas, recipes, runs, drift, approvals)."""

from __future__ import annotations

import os

from lenses.orchestration_graph.feature_flag import experimental_orchestration_graph_enabled


def experimental_agentic_bridge_b3_enabled() -> bool:
    """On when orchestration graph is on. Set ``LENSES_EXPERIMENTAL_AGENTIC_BRIDGE_B3=0`` to disable."""
    if not experimental_orchestration_graph_enabled():
        return False
    raw = (os.environ.get("LENSES_EXPERIMENTAL_AGENTIC_BRIDGE_B3") or "").strip().lower()
    if raw in ("0", "false", "no", "off"):
        return False
    if not raw:
        return True
    return raw in ("1", "true", "yes", "on")
