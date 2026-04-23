"""Compare Forge config, registry expectations, and on-disk Cursor rules (drift)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from lenses.bridge.agentic_discovery import discover_forge_config, list_cursor_rules


def compute_agentic_drift(workspace_root: Path, reg: dict[str, Any]) -> dict[str, Any]:
    cfg = discover_forge_config(workspace_root)
    rules = list_cursor_rules(workspace_root)
    basenames = {r["basename"] for r in rules}

    discipline_map: dict[str, list[str]] = reg.get("expected_cursor_rules_by_discipline") or {}
    active_disciplines: list[str] = list(cfg.get("active_disciplines") or [])

    missing_expected: list[dict[str, Any]] = []
    for disc in active_disciplines:
        expected_files = discipline_map.get(disc) or []
        for fname in expected_files:
            if fname not in basenames:
                # allow case-insensitive match
                if fname.lower() not in {b.lower() for b in basenames}:
                    missing_expected.append(
                        {
                            "discipline": disc,
                            "expected_file": fname,
                            "reason": "not_found_under_.cursor/rules",
                        }
                    )

    # Orphan heuristic: versona-*.mdc present but discipline not active (soft signal)
    orphaned: list[dict[str, Any]] = []
    for r in rules:
        bn = r["basename"].lower()
        if not bn.startswith("versona-") and not bn.startswith("forge-"):
            continue
        # map file back to any discipline that lists it
        matched_disc = [
            d for d, files in discipline_map.items() if any(f.lower() == bn for f in files)
        ]
        if not matched_disc:
            orphaned.append(
                {
                    "basename": r["basename"],
                    "reason": "no_registry_discipline_maps_this_file",
                }
            )
            continue
        for d in matched_disc:
            if d not in active_disciplines:
                orphaned.append(
                    {
                        "basename": r["basename"],
                        "discipline": d,
                        "reason": "discipline_not_active_in_forge_config",
                    }
                )

    aligned = len(missing_expected) == 0 and cfg.get("ok") is True

    return {
        "ok": True,
        "aligned": aligned,
        "forge_config_present": cfg.get("present"),
        "forge_config_ok": cfg.get("ok"),
        "active_versona_families": cfg.get("active_versona_families") or [],
        "active_disciplines": active_disciplines,
        "cursor_rule_count": len(rules),
        "missing_expected_rules": missing_expected,
        "orphaned_or_unmatched_rules": orphaned,
        "note": "Orphan list is heuristic: versona-/forge- files vs active disciplines in forge.config.yaml.",
    }


def build_drift_report_payload(workspace_root: Path, reg: dict[str, Any]) -> dict[str, Any]:
    from lenses.bridge.agentic_discovery import build_rules_manifest

    drift = compute_agentic_drift(workspace_root, reg)
    manifest = build_rules_manifest(workspace_root, reg)
    return {"drift": drift, "rules_manifest": manifest}
