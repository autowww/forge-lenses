"""Build ``GET /api/cross-team-release/overview`` — Sprint 7."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from lenses.cross_team_release.artifacts import build_communication_artifacts
from lenses.cross_team_release.board import build_dependency_board
from lenses.cross_team_release.calendar import build_release_calendar
from lenses.cross_team_release.feature_flag import experimental_cross_team_release_enabled
from lenses.cross_team_release.local_store import load_demo_fixture, read_local_cross_team_release
from lenses.cross_team_release.normalized import SCHEMA_VERSION, empty_cross_team_overview
from lenses.cross_team_release.packet import build_go_no_go_packet


def _lenses_root() -> Path:
    return Path(__file__).resolve().parent.parent


def _truthy_env(name: str) -> bool:
    raw = (os.environ.get(name) or "").strip().lower()
    return raw in ("1", "true", "yes", "on")


def _load_doc(workspace_root: Path) -> dict[str, Any] | None:
    doc = read_local_cross_team_release(workspace_root)
    if doc is not None:
        return doc
    if _truthy_env("LENSES_CROSS_TEAM_RELEASE_SEED_DEMO"):
        return load_demo_fixture(_lenses_root())
    return None


def build_cross_team_release_overview(
    *,
    workspace_root: Path,
    scan_state: dict[str, Any],
    force_flag: bool | None = None,
) -> dict[str, Any]:
    enabled = experimental_cross_team_release_enabled() if force_flag is None else bool(force_flag)
    children = scan_state.get("children")
    if not isinstance(children, list):
        children = []
    git_count = sum(1 for c in children if isinstance(c, dict) and c.get("is_git"))

    if not enabled:
        base = empty_cross_team_overview()
        return {
            "ok": True,
            **base,
            "feature_enabled": False,
            "provider_kind": "disabled",
            "resolved_at": scan_state.get("resolved_at"),
            "workspace_summary": {"child_count": len(children), "git_repo_count": git_count},
            "live_enrichment": {},
            "hints": [
                "Cross-team release orchestration is off (LENSES_EXPERIMENTAL_CROSS_TEAM_RELEASE=0).",
                "When on, use `.lenses-local/cross-team-release.json` or LENSES_CROSS_TEAM_RELEASE_SEED_DEMO=1.",
            ],
        }

    raw_doc = _load_doc(workspace_root)
    if raw_doc is None:
        base = empty_cross_team_overview()
        return {
            "ok": True,
            **base,
            "feature_enabled": True,
            "provider_kind": "scan_only",
            "resolved_at": scan_state.get("resolved_at"),
            "workspace_summary": {"child_count": len(children), "git_repo_count": git_count},
            "live_enrichment": {},
            "hints": [
                "No `.lenses-local/cross-team-release.json` — add one or set "
                "LENSES_CROSS_TEAM_RELEASE_SEED_DEMO=1 for dependency board, CAB, change requests, and packets.",
            ],
        }

    doc = dict(raw_doc)
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

    devsecops: dict[str, Any] | None = None
    from lenses.devsecops_compliance.aggregate import build_devsecops_overview_payload
    from lenses.devsecops_compliance.feature_flag import experimental_devsecops_compliance_enabled

    if experimental_devsecops_compliance_enabled():
        devsecops = build_devsecops_overview_payload(
            workspace_root=workspace_root,
            scan_state=scan_state,
            force_flag=None,
        )

    board = build_dependency_board(doc, children)
    cal = build_release_calendar(doc, cicd)
    packet = build_go_no_go_packet(doc, cicd, quality, devsecops)
    comms = build_communication_artifacts(doc, cicd, quality, devsecops, packet)

    hints: list[str] = []
    if cicd.get("provider_kind") == "scan_only":
        hints.append("CI/CD fixture missing — go/no-go packet blockers omit live promotion data.")
    if isinstance(quality, dict) and quality.get("provider_kind") == "scan_only":
        hints.append("Test-quality fixture missing — quality train line may be empty.")
    if isinstance(devsecops, dict) and devsecops.get("provider_kind") == "scan_only":
        hints.append("DevSecOps fixture missing — security gate line may be empty.")

    return {
        "ok": True,
        "schema_version": SCHEMA_VERSION,
        "feature_enabled": True,
        "provider_kind": "local_fixture",
        "resolved_at": scan_state.get("resolved_at"),
        "workspace_summary": {"child_count": len(children), "git_repo_count": git_count},
        "focus_release_version": str(doc.get("focus_release_version") or ""),
        "teams": [t for t in doc.get("teams") or [] if isinstance(t, dict)],
        "initiatives": [i for i in doc.get("initiatives") or [] if isinstance(i, dict)],
        "readiness_views": [r for r in doc.get("readiness_views") or [] if isinstance(r, dict)],
        "dependency_board": board,
        "dependency_edges": [e for e in doc.get("dependency_edges") or [] if isinstance(e, dict)],
        "release_calendar": cal,
        "change_requests": [c for c in doc.get("change_requests") or [] if isinstance(c, dict)],
        "cab_sessions": [c for c in doc.get("cab_sessions") or [] if isinstance(c, dict)],
        "go_no_go_packet": packet,
        "communication_artifacts": comms,
        "live_enrichment": {
            "cicd_ok": bool(cicd.get("ok")),
            "cicd_provider_kind": cicd.get("provider_kind"),
            "release_train": cicd.get("release_train"),
            "blocked_promotions": cicd.get("blocked_promotions") or [],
            "rollback_targets": cicd.get("rollback_targets") or [],
            "what_is_live": cicd.get("what_is_live") or [],
            "freeze_windows": cicd.get("freeze_windows") or [],
            "promotions": cicd.get("promotions") or [],
        },
        "hints": hints,
    }
