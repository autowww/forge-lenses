"""Build ``GET /api/quality/overview`` and per-project quality payloads."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from lenses.test_quality.feature_flag import experimental_test_quality_enabled
from lenses.test_quality.gates import build_run_comparisons, evaluate_quality_gates
from lenses.test_quality.local_store import load_demo_fixture, read_local_test_quality
from lenses.test_quality.normalized import SCHEMA_VERSION, empty_quality_overview


def _lenses_root() -> Path:
    return Path(__file__).resolve().parent.parent


def _truthy_env(name: str) -> bool:
    raw = (os.environ.get(name) or "").strip().lower()
    return raw in ("1", "true", "yes", "on")


def _load_doc(workspace_root: Path) -> dict[str, Any] | None:
    doc = read_local_test_quality(workspace_root)
    if doc is not None:
        return doc
    if _truthy_env("LENSES_TEST_QUALITY_SEED_DEMO"):
        return load_demo_fixture(_lenses_root())
    return None


def _filter_by_project(doc: dict[str, Any], project: str) -> dict[str, Any]:
    if not project:
        return doc

    def has_proj(row: dict[str, Any]) -> bool:
        return str(row.get("project") or "").strip() == project

    out = dict(doc)
    for key in (
        "test_plans",
        "test_suites",
        "test_cases",
        "test_runs",
        "defects",
        "coverage_summaries",
        "flaky_test_signals",
    ):
        rows = doc.get(key) or []
        out[key] = [r for r in rows if isinstance(r, dict) and has_proj(r)]
    uats = [u for u in doc.get("uat_signoffs") or [] if isinstance(u, dict)]
    out["uat_signoffs"] = uats
    ev = [e for e in doc.get("evidence_attachments") or [] if isinstance(e, dict) and has_proj(e)]
    out["evidence_attachments"] = ev
    out["quality_gates"] = list(doc.get("quality_gates") or [])
    out["regression_packs"] = [r for r in doc.get("regression_packs") or [] if isinstance(r, dict)]
    out["release_readiness_checklists"] = list(doc.get("release_readiness_checklists") or [])
    return out


def build_quality_overview_payload(
    *,
    workspace_root: Path,
    scan_state: dict[str, Any],
    force_flag: bool | None = None,
) -> dict[str, Any]:
    enabled = experimental_test_quality_enabled() if force_flag is None else bool(force_flag)
    children = scan_state.get("children")
    if not isinstance(children, list):
        children = []
    child_names = {str(c.get("name") or "").strip() for c in children if isinstance(c, dict)}
    child_names.discard("")

    if not enabled:
        base = empty_quality_overview()
        return {
            "ok": True,
            **base,
            "feature_enabled": False,
            "provider_kind": "disabled",
            "resolved_at": scan_state.get("resolved_at"),
            "workspace_summary": {"child_count": len(children), "git_repo_count": sum(1 for c in children if isinstance(c, dict) and c.get("is_git"))},
            "hints": [
                "Test management and quality gates are off (LENSES_EXPERIMENTAL_TEST_QUALITY=0).",
                "When on, use `.lenses-local/test-quality.json` or LENSES_TEST_QUALITY_SEED_DEMO=1.",
            ],
        }

    doc = _load_doc(workspace_root)
    if doc is None:
        base = empty_quality_overview()
        return {
            "ok": True,
            **base,
            "feature_enabled": True,
            "provider_kind": "scan_only",
            "resolved_at": scan_state.get("resolved_at"),
            "workspace_summary": {
                "child_count": len(children),
                "git_repo_count": sum(1 for c in children if isinstance(c, dict) and c.get("is_git")),
            },
            "hints": [
                "No `.lenses-local/test-quality.json` — add one or set LENSES_TEST_QUALITY_SEED_DEMO=1 "
                "for the demo (gates, runs, defects, UAT, checklists).",
            ],
        }

    runs = [r for r in doc.get("test_runs") or [] if isinstance(r, dict)]
    evaluations, release_quality = evaluate_quality_gates(doc, project_filter=None)
    comparisons = build_run_comparisons(runs)

    return {
        "ok": True,
        "schema_version": SCHEMA_VERSION,
        "feature_enabled": True,
        "provider_kind": "local_fixture",
        "resolved_at": scan_state.get("resolved_at"),
        "workspace_summary": {
            "child_count": len(children),
            "git_repo_count": sum(1 for c in children if isinstance(c, dict) and c.get("is_git")),
        },
        "test_plans": [p for p in doc.get("test_plans") or [] if isinstance(p, dict)],
        "test_suites": [s for s in doc.get("test_suites") or [] if isinstance(s, dict)],
        "test_cases": [c for c in doc.get("test_cases") or [] if isinstance(c, dict)],
        "test_runs": runs[:120],
        "defects": [d for d in doc.get("defects") or [] if isinstance(d, dict)],
        "coverage_summaries": [c for c in doc.get("coverage_summaries") or [] if isinstance(c, dict)],
        "flaky_test_signals": [f for f in doc.get("flaky_test_signals") or [] if isinstance(f, dict)],
        "quality_gates": [g for g in doc.get("quality_gates") or [] if isinstance(g, dict)],
        "gate_evaluations": evaluations,
        "uat_signoffs": [u for u in doc.get("uat_signoffs") or [] if isinstance(u, dict)],
        "regression_packs": [r for r in doc.get("regression_packs") or [] if isinstance(r, dict)],
        "release_readiness_checklists": [x for x in doc.get("release_readiness_checklists") or [] if isinstance(x, dict)],
        "evidence_attachments": [e for e in doc.get("evidence_attachments") or [] if isinstance(e, dict)],
        "release_quality": release_quality,
        "run_comparisons": comparisons,
        "hints": [],
    }


def build_project_quality_payload(
    *,
    workspace_root: Path,
    scan_state: dict[str, Any],
    project_name: str,
    force_flag: bool | None = None,
) -> dict[str, Any]:
    overview = build_quality_overview_payload(
        workspace_root=workspace_root,
        scan_state=scan_state,
        force_flag=force_flag,
    )
    pn = (project_name or "").strip()
    if not overview.get("feature_enabled"):
        return {**overview, "project": pn, "quality_summary": None}

    if overview.get("provider_kind") != "local_fixture":
        return {
            "ok": True,
            "schema_version": SCHEMA_VERSION,
            "feature_enabled": True,
            "provider_kind": overview.get("provider_kind"),
            "resolved_at": overview.get("resolved_at"),
            "project": pn,
            "quality_summary": None,
            "hints": overview.get("hints") or [],
        }

    doc = _load_doc(workspace_root)
    assert doc is not None
    filtered = _filter_by_project(doc, pn)
    runs = [r for r in filtered.get("test_runs") or [] if isinstance(r, dict)]
    evaluations, release_quality = evaluate_quality_gates(filtered, project_filter=pn)
    comparisons = build_run_comparisons(runs)

    open_defects = sum(
        1
        for d in filtered.get("defects") or []
        if isinstance(d, dict) and str(d.get("status") or "").lower() not in ("closed", "done", "resolved")
    )
    failed_gates = sum(1 for e in evaluations if not e.get("passed"))

    summary = {
        "project": pn,
        "open_defects": open_defects,
        "failed_gates": failed_gates,
        "gates_passed": len(evaluations) - failed_gates,
        "latest_run_by_suite": _latest_by_suite(runs),
        "release_quality": release_quality,
    }

    return {
        "ok": True,
        "schema_version": SCHEMA_VERSION,
        "feature_enabled": True,
        "provider_kind": "local_fixture",
        "resolved_at": overview.get("resolved_at"),
        "project": pn,
        "quality_summary": summary,
        "gate_evaluations": evaluations,
        "test_runs": runs[:40],
        "defects": [d for d in filtered.get("defects") or [] if isinstance(d, dict)],
        "coverage_summaries": [c for c in filtered.get("coverage_summaries") or [] if isinstance(c, dict)],
        "flaky_test_signals": [f for f in filtered.get("flaky_test_signals") or [] if isinstance(f, dict)],
        "run_comparisons": comparisons,
        "hints": [],
    }


def _latest_by_suite(runs: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for r in runs:
        sid = str(r.get("suite_id") or "")
        if not sid:
            continue
        prev = out.get(sid)
        ts = str(r.get("finished_at") or r.get("started_at") or "")
        if prev is None or ts > str(prev.get("finished_at") or prev.get("started_at") or ""):
            out[sid] = r
    return out
