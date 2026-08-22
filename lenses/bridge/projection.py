"""Project neutral / OGS entities into Forge, SDLC, and PDLC lenses."""

from __future__ import annotations

from typing import Any, Literal

from lenses.bridge.registry import BridgeRegistry

Lens = Literal["neutral", "forge", "sdlc", "pdlc"]


def _forge_subtype_for_ogs(entity: dict[str, Any], canonical: str) -> str | None:
    kind = str(entity.get("kind") or "")
    payload = entity.get("payload") if isinstance(entity.get("payload"), dict) else {}
    if canonical == "work_unit" and kind == "story":
        if payload.get("forge_spark"):
            return "spark_execution"
        return "story_default"
    if canonical == "work_unit" and kind == "task":
        return "tasklet"
    return None


def project_entity(
    entity: dict[str, Any],
    reg: BridgeRegistry,
    lens: Lens,
) -> dict[str, Any]:
    """Return a projection view for one graph entity (OGS row shape)."""
    kind = str(entity.get("kind") or "")
    canonical = reg.ogs_kind_to_canonical(kind)
    term_row = reg.lookup_neutral_term(canonical) or {}

    base = {
        "entity_id": entity.get("id"),
        "ogs_kind": kind,
        "canonical_kind": canonical,
        "display_name": entity.get("display_name"),
        "summary": entity.get("summary") or "",
        "source_system": entity.get("source_system") or "",
        "source_record_id": entity.get("source_record_id") or "",
        "external_ref": entity.get("external_ref") or "",
    }

    if lens == "neutral":
        return {
            **base,
            "labels": {
                "primary": canonical.replace("_", " "),
                "terminology": term_row,
            },
            "forge_subtype": _forge_subtype_for_ogs(entity, canonical),
        }

    if lens == "forge":
        labels = list(term_row.get("forge_labels") or [])
        return {
            **base,
            "labels": labels,
            "subtitle": "Forge SDLC",
            "conflict_notes": term_row.get("conflict_notes"),
            "forge_subtype": _forge_subtype_for_ogs(entity, canonical),
        }

    if lens == "sdlc":
        return {
            **base,
            "labels": list(term_row.get("sdlc_labels") or []),
            "subtitle": "SDLC",
            "conflict_notes": term_row.get("conflict_notes"),
        }

    return {
        **base,
        "labels": list(term_row.get("pdlc_labels") or []),
        "subtitle": "PDLC",
        "conflict_notes": term_row.get("conflict_notes"),
    }


def project_trace_nodes(
    nodes: list[dict[str, Any]],
    reg: BridgeRegistry,
    lens: Lens,
) -> list[dict[str, Any]]:
    return [project_entity(n, reg, lens) for n in nodes]
