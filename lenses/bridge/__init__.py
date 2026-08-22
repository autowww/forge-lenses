"""Methodology bridge: neutral spine projections and versioned term registry."""

from __future__ import annotations

from lenses.bridge.feature_flag import experimental_bridge_spine_enabled
from lenses.bridge.registry import BridgeRegistry, load_bridge_registry, validate_registry_struct
from lenses.bridge.trace_service import (
    bridge_impact_payload,
    bridge_provenance_payload,
    bridge_trace_payload,
    compute_gaps,
    compute_traceability_score,
    immediate_neighbors,
    spine_meta_for_entity,
)

__all__ = [
    "BridgeRegistry",
    "bridge_impact_payload",
    "bridge_provenance_payload",
    "bridge_trace_payload",
    "compute_gaps",
    "compute_traceability_score",
    "experimental_bridge_spine_enabled",
    "immediate_neighbors",
    "load_bridge_registry",
    "spine_meta_for_entity",
    "validate_registry_struct",
]
