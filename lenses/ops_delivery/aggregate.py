"""Build ``GET /api/ops-delivery/overview``."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from lenses.ops_delivery.dora import compute_dora_metrics
from lenses.ops_delivery.feature_flag import experimental_ops_delivery_enabled
from lenses.ops_delivery.ingest import expand_ingestions
from lenses.ops_delivery.local_store import load_demo_fixture, read_local_ops_delivery
from lenses.ops_delivery.normalized import SCHEMA_VERSION, empty_ops_delivery_overview
from lenses.ops_delivery.postmortem_templates import merged_templates
from lenses.ops_delivery.rollback_signals import build_rollback_signals


def _lenses_root() -> Path:
    return Path(__file__).resolve().parent.parent


def _truthy_env(name: str) -> bool:
    raw = (os.environ.get(name) or "").strip().lower()
    return raw in ("1", "true", "yes", "on")


def _load_doc(workspace_root: Path) -> dict[str, Any] | None:
    doc = read_local_ops_delivery(workspace_root)
    if doc is not None:
        return doc
    if _truthy_env("LENSES_OPS_DELIVERY_SEED_DEMO"):
        return load_demo_fixture(_lenses_root())
    return None


def _enrich_incident_traces(incidents: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for raw in incidents:
        row = dict(raw)
        trace = {
            "release_version": str(row.get("linked_release_version") or ""),
            "environment_id": str(row.get("linked_environment_id") or ""),
            "story_ids": [str(x) for x in (row.get("linked_story_ids") or [])],
            "promotion_id": str(row.get("linked_promotion_id") or ""),
        }
        row["traceability"] = trace
        out.append(row)
    return out


def build_ops_delivery_overview(
    *,
    workspace_root: Path,
    scan_state: dict[str, Any],
    force_flag: bool | None = None,
) -> dict[str, Any]:
    enabled = experimental_ops_delivery_enabled() if force_flag is None else bool(force_flag)
    children = scan_state.get("children")
    if not isinstance(children, list):
        children = []
    git_count = sum(1 for c in children if isinstance(c, dict) and c.get("is_git"))

    if not enabled:
        base = empty_ops_delivery_overview()
        return {
            "ok": True,
            **base,
            "feature_enabled": False,
            "provider_kind": "disabled",
            "resolved_at": scan_state.get("resolved_at"),
            "workspace_summary": {"child_count": len(children), "git_repo_count": git_count},
            "hints": [
                "Ops delivery metrics are off (LENSES_EXPERIMENTAL_OPS_DELIVERY=0).",
                "When on, use `.lenses-local/ops-delivery.json` or LENSES_OPS_DELIVERY_SEED_DEMO=1.",
            ],
        }

    raw_doc = _load_doc(workspace_root)
    if raw_doc is None:
        base = empty_ops_delivery_overview()
        return {
            "ok": True,
            **base,
            "feature_enabled": True,
            "provider_kind": "scan_only",
            "resolved_at": scan_state.get("resolved_at"),
            "workspace_summary": {"child_count": len(children), "git_repo_count": git_count},
            "hints": [
                "No `.lenses-local/ops-delivery.json` — add one or set LENSES_OPS_DELIVERY_SEED_DEMO=1.",
            ],
        }

    from lenses.cicd_orchestration import build_cicd_control_tower_payload

    cicd = build_cicd_control_tower_payload(
        workspace_root=workspace_root,
        scan_state=scan_state,
        force_flag=None,
    )

    quality: dict[str, Any] | None = None
    from lenses.test_quality.aggregate import build_quality_overview_payload
    from lenses.test_quality.feature_flag import experimental_test_quality_enabled

    if experimental_test_quality_enabled():
        quality = build_quality_overview_payload(
            workspace_root=workspace_root,
            scan_state=scan_state,
            force_flag=None,
        )

    doc = expand_ingestions(dict(raw_doc))
    window_days = int(doc.get("dora_window_days") or 30)

    incidents = _enrich_incident_traces([i for i in doc.get("incidents") or [] if isinstance(i, dict)])
    dora = compute_dora_metrics(cicd, doc, quality=quality, window_days=window_days)
    rollback = build_rollback_signals(cicd, doc)
    templates = merged_templates(doc)

    hints: list[str] = []
    if cicd.get("provider_kind") == "scan_only":
        hints.append("CI/CD fixture missing — DORA deploy frequency and lead time may be thin.")
    if isinstance(quality, dict) and quality.get("provider_kind") == "scan_only":
        hints.append("Test-quality fixture missing — rework open_defects may be zero.")

    return {
        "ok": True,
        "schema_version": SCHEMA_VERSION,
        "feature_enabled": True,
        "provider_kind": "local_fixture",
        "resolved_at": scan_state.get("resolved_at"),
        "workspace_summary": {"child_count": len(children), "git_repo_count": git_count},
        "services": [s for s in doc.get("services") or [] if isinstance(s, dict)],
        "slis": [s for s in doc.get("slis") or [] if isinstance(s, dict)],
        "slos": [s for s in doc.get("slos") or [] if isinstance(s, dict)],
        "incidents": incidents[:200],
        "postmortems": [p for p in doc.get("postmortems") or [] if isinstance(p, dict)][:120],
        "error_budget_events": [e for e in doc.get("error_budget_events") or [] if isinstance(e, dict)][:200],
        "feature_flag_exposures": [f for f in doc.get("feature_flag_exposures") or [] if isinstance(f, dict)][:200],
        "dora_metrics": dora,
        "rollback_signals": rollback,
        "postmortem_templates": templates,
        "hints": hints,
    }
