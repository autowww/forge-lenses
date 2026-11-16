"""Test management, gates, and CICD merge (Sprint 5)."""

from __future__ import annotations

from pathlib import Path

import pytest

from lenses.cicd_orchestration.aggregate import build_cicd_control_tower_payload
from lenses.test_quality.aggregate import build_project_quality_payload, build_quality_overview_payload
from lenses.test_quality.feature_flag import experimental_test_quality_enabled
from lenses.test_quality.gates import evaluate_quality_gates, quality_gate_promotion_blockers


def test_quality_disabled(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("LENSES_EXPERIMENTAL_TEST_QUALITY", "0")
    assert experimental_test_quality_enabled() is False
    scan = {"children": [], "resolved_at": "t"}
    out = build_quality_overview_payload(workspace_root=tmp_path, scan_state=scan, force_flag=False)
    assert out["feature_enabled"] is False


def test_quality_demo_seed(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.delenv("LENSES_EXPERIMENTAL_TEST_QUALITY", raising=False)
    monkeypatch.setenv("LENSES_TEST_QUALITY_SEED_DEMO", "1")
    scan = {"children": [{"name": "forgesdlc", "is_git": True}], "resolved_at": "t"}
    out = build_quality_overview_payload(workspace_root=tmp_path, scan_state=scan, force_flag=True)
    assert out["feature_enabled"] is True
    assert len(out["test_cases"]) >= 2
    assert len(out["gate_evaluations"]) >= 2
    failed = [e for e in out["gate_evaluations"] if not e["passed"]]
    assert len(failed) >= 1
    rq = out.get("release_quality") or {}
    assert rq.get("ready") is False
    assert len(out["run_comparisons"]) >= 1


def test_quality_gates_block_promotions(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("LENSES_TEST_QUALITY_SEED_DEMO", "1")
    from lenses.test_quality.local_store import load_demo_fixture

    lenses_root = Path(__file__).resolve().parent.parent / "lenses"
    doc = load_demo_fixture(lenses_root)
    assert doc is not None
    ev, _ = evaluate_quality_gates(doc, project_filter="forgesdlc")
    promos = [
        {"id": "promo-stg-prod-1", "from_env": "staging", "to_env": "production"},
        {"id": "promo-dev-stg-1", "from_env": "dev", "to_env": "staging"},
    ]
    blocked = quality_gate_promotion_blockers(ev, promos)
    reasons = {str(b.get("reason")) for b in blocked}
    assert any(r.startswith("quality_gate_failed:") for r in reasons)


def test_cicd_merges_quality_blockers(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("LENSES_CICD_ORCHESTRATION_SEED_DEMO", "1")
    monkeypatch.setenv("LENSES_TEST_QUALITY_SEED_DEMO", "1")
    scan = {"children": [{"name": "forgesdlc", "is_git": True}], "resolved_at": "t"}
    out = build_cicd_control_tower_payload(workspace_root=tmp_path, scan_state=scan, force_flag=True)
    reasons = [str(b.get("reason")) for b in out["blocked_promotions"]]
    assert any(r.startswith("quality_gate_failed:") for r in reasons)


def test_project_quality_payload(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("LENSES_TEST_QUALITY_SEED_DEMO", "1")
    scan = {"children": [{"name": "forgesdlc", "is_git": True}], "resolved_at": "t"}
    out = build_project_quality_payload(
        workspace_root=tmp_path,
        scan_state=scan,
        project_name="forgesdlc",
        force_flag=True,
    )
    assert out.get("quality_summary") is not None
    assert out["quality_summary"]["open_defects"] >= 1
