"""
Capability-based endpoint registry for tasklets (Sprint 5).

Tasklets request semantic capabilities (``triage.small``, ``writer.medium``, …) instead of
ad-hoc slot names or model IDs. Legacy ``local_*`` slot ids are normalized to these canonical ids.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from lenses.agent_runtime.types import EndpointCapability

# --- Canonical capability ids (use in docs-health agents and settings) -----------------

CAPABILITY_TRIAGE_SMALL = "triage.small"
CAPABILITY_WRITER_MEDIUM = "writer.medium"
CAPABILITY_REVIEWER_HIGH = "reviewer.high"

_LEGACY_TO_CANONICAL: dict[str, str] = {
    "local_triage": CAPABILITY_TRIAGE_SMALL,
    "local_writer": CAPABILITY_WRITER_MEDIUM,
    "local_reviewer": CAPABILITY_REVIEWER_HIGH,
}


def normalize_slot_id(slot: str) -> str:
    """Map deprecated ``local_*`` ids to canonical capability ids."""
    s = str(slot or "").strip()
    return _LEGACY_TO_CANONICAL.get(s, s)


def docs_health_slot_lookup_keys(slot: str) -> list[str]:
    """Keys to try in ``docs_health_slots`` JSON (canonical + legacy + requested)."""
    s = str(slot or "").strip()
    out: list[str] = []
    canon = normalize_slot_id(s)
    for k in (s, canon):
        if k and k not in out:
            out.append(k)
    for leg, c in _LEGACY_TO_CANONICAL.items():
        if c == canon and leg not in out:
            out.append(leg)
    return out


def default_endpoint_capabilities() -> list[EndpointCapability]:
    """Registry surface for Admin / inspect (no live network calls)."""
    return [
        {
            "id": CAPABILITY_TRIAGE_SMALL,
            "label": "Triage (small)",
            "family": "triage",
            "tier": "small",
            "description": "Cluster context, enrichment, and brief agents — prefer local Ollama.",
        },
        {
            "id": CAPABILITY_WRITER_MEDIUM,
            "label": "Writer (medium)",
            "family": "writer",
            "tier": "medium",
            "description": "Markdown / diagram / ADR drafting — prefer local, then private URL, then cloud.",
        },
        {
            "id": CAPABILITY_REVIEWER_HIGH,
            "label": "Reviewer (high)",
            "family": "reviewer",
            "tier": "high",
            "description": "Structured review JSON — same routing profile as writer; tier encodes expected rigor.",
        },
    ]


def build_endpoint_registry_payload(workspace_root: Path) -> dict[str, Any]:
    """Summary for ``/api/agent-runtime/overview`` and tooling."""
    from lenses.agent_runtime.capabilities import build_provider_endpoints, build_routing_policy_summary, default_model_slots

    return {
        "capabilities": [dict(x) for x in default_endpoint_capabilities()],
        "slots": default_model_slots(),
        "providers": build_provider_endpoints(workspace_root),
        "policy": build_routing_policy_summary(workspace_root),
        "legacy_slot_aliases": dict(_LEGACY_TO_CANONICAL),
    }
