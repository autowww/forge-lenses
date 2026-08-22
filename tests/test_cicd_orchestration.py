"""CI/CD control tower aggregate and adapters (Sprint 4)."""

from __future__ import annotations

from pathlib import Path

import pytest

from lenses.cicd_orchestration.adapters.github_actions import normalize_github_actions_run
from lenses.cicd_orchestration.aggregate import build_cicd_control_tower_payload
from lenses.cicd_orchestration.feature_flag import experimental_cicd_orchestration_enabled


def test_github_actions_normalizer() -> None:
    raw = {
        "id": 1,
        "name": "CI",
        "status": "completed",
        "conclusion": "success",
        "head_sha": "abc",
        "head_branch": "main",
        "html_url": "https://example/run/1",
        "jobs": [{"name": "unit", "conclusion": "success", "started_at": "t0", "completed_at": "t1"}],
    }
    out = normalize_github_actions_run(raw, project="p")
    assert out["provider"] == "github_actions"
    assert out["stages"][0]["name"] == "unit"


def test_control_tower_disabled(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("LENSES_EXPERIMENTAL_CICD_ORCHESTRATION", "0")
    assert experimental_cicd_orchestration_enabled() is False
    scan = {"children": [{"name": "forgesdlc", "is_git": True}], "resolved_at": "t"}
    out = build_cicd_control_tower_payload(workspace_root=tmp_path, scan_state=scan, force_flag=False)
    assert out["feature_enabled"] is False


def test_control_tower_demo_seed(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.delenv("LENSES_EXPERIMENTAL_CICD_ORCHESTRATION", raising=False)
    monkeypatch.setenv("LENSES_CICD_ORCHESTRATION_SEED_DEMO", "1")
    scan = {"children": [{"name": "forgesdlc", "is_git": True}], "resolved_at": "t"}
    out = build_cicd_control_tower_payload(workspace_root=tmp_path, scan_state=scan, force_flag=True)
    assert out["feature_enabled"] is True
    assert len(out["pipeline_runs"]) >= 4
    assert len(out["environments"]) >= 3
    assert out["release_train"] is not None
    assert len(out["what_is_live"]) >= 3
    blocked_ids = {str(b.get("promotion_id")) for b in out["blocked_promotions"]}
    assert "promo-stg-prod-1" in blocked_ids
