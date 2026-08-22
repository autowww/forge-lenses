"""Sprint B6: PDLC outcome bridge (launch → signals → learning → Ore)."""

from __future__ import annotations

import os

from lenses.orchestration_graph.feature_flag import experimental_orchestration_graph_enabled


def experimental_outcome_bridge_b6_enabled() -> bool:
    """On when orchestration graph is on. Set ``LENSES_EXPERIMENTAL_OUTCOME_BRIDGE_B6=0`` to disable."""
    if not experimental_orchestration_graph_enabled():
        return False
    raw = (os.environ.get("LENSES_EXPERIMENTAL_OUTCOME_BRIDGE_B6") or "").strip().lower()
    if raw in ("0", "false", "no", "off"):
        return False
    if not raw:
        return True
    return raw in ("1", "true", "yes", "on")
