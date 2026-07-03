"""Autonomy maturity assessment: signals, scoring, and payload shapes."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from lenses.autonomy_maturity.aggregate import build_overview_payload, build_project_payload
from lenses.autonomy_maturity.feature_flag import experimental_autonomy_maturity_enabled


def _seed_gates(repo: Path) -> None:
    (repo / "forge").mkdir(parents=True)
    (repo / "forge" / "forge.config.yaml").write_text(
        "assay:\n  tests_pass: required\n  acceptance_criteria_met: required\n  risks_reviewed: required\n",
        encoding="utf-8",
    )
    (repo / ".cursor" / "rules").mkdir(parents=True)
    (repo / ".cursor" / "rules" / "forge.mdc").write_text("# rule\n", encoding="utf-8")
    (repo / ".github" / "workflows").mkdir(parents=True)
    (repo / ".github" / "workflows" / "ci.yml").write_text("on: push\n", encoding="utf-8")
    (repo / "tests").mkdir()
    (repo / "tests" / "test_smoke.py").write_text("def test_ok():\n    assert True\n", encoding="utf-8")


def _seed_run(repo: Path, idx: int, *, level: str, sublevel: str | None, ok: bool, escalated: bool | None) -> None:
    md = repo / "runs" / "campaigns" / "c1" / f"item-{idx}" / f"run-{idx}" / "machine"
    md.mkdir(parents=True)
    (md / "assay.json").write_text(
        json.dumps({"ok": ok, "level": level, "sublevel": sublevel}), encoding="utf-8"
    )
    if escalated is not None:
        (md / "run.json").write_text(json.dumps({"escalated": escalated}), encoding="utf-8")


def test_feature_flag_default_off(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("LENSES_EXPERIMENTAL_AUTONOMY_MATURITY", raising=False)
    assert experimental_autonomy_maturity_enabled() is False
    monkeypatch.setenv("LENSES_EXPERIMENTAL_AUTONOMY_MATURITY", "1")
    assert experimental_autonomy_maturity_enabled() is True


def test_bare_repo_scores_l0a_with_recommendations(tmp_path: Path) -> None:
    report = build_project_payload(tmp_path, "bare")
    assert report["observed_level"] == "L0"
    assert report["observed_grade"] == "a"
    assert report["claim"] == "L0a in bare"
    assert report["score"] == 0
    assert len(report["recommendations"]) >= 3


def test_gates_only_scores_gate_component(tmp_path: Path) -> None:
    _seed_gates(tmp_path)
    report = build_project_payload(tmp_path, "gated")
    assert report["observed_level"] == "L0"
    assert report["components"]["gate_definition"] == 1.0
    assert report["score"] == 40
    assert any("No unattended runs" in r for r in report["recommendations"])


def test_single_green_run_earns_grade_b(tmp_path: Path) -> None:
    _seed_gates(tmp_path)
    _seed_run(tmp_path, 0, level="L2", sublevel="L2.2", ok=True, escalated=False)
    report = build_project_payload(tmp_path, "demo")
    assert report["observed_level"] == "L2"
    assert report["observed_sublevel"] == "L2.2"
    assert report["observed_grade"] == "b"
    assert report["claim"] == "L2.2b in demo"
    assert 70 <= report["score"] < 100
    assert any("promote it to L2.2c" in r for r in report["recommendations"])


def test_five_green_runs_low_escalation_earns_grade_c(tmp_path: Path) -> None:
    _seed_gates(tmp_path)
    for i in range(5):
        _seed_run(tmp_path, i, level="L2", sublevel="L2.2", ok=True, escalated=(i == 0))
    report = build_project_payload(tmp_path, "repeat")
    assert report["observed_grade"] == "c"
    assert report["components"]["repeatability"] == 1.0
    assert report["components"]["operational_metrics"] == 0.5
    assert any("grade d" in r for r in report["recommendations"])


def test_high_escalation_blocks_grade_c(tmp_path: Path) -> None:
    _seed_gates(tmp_path)
    for i in range(5):
        _seed_run(tmp_path, i, level="L1", sublevel=None, ok=True, escalated=(i < 3))
    report = build_project_payload(tmp_path, "hot")
    assert report["observed_grade"] == "b"
    assert any("escalation rate" in r for r in report["recommendations"])


def test_failed_runs_do_not_count(tmp_path: Path) -> None:
    _seed_gates(tmp_path)
    _seed_run(tmp_path, 0, level="L3", sublevel="L3.1", ok=False, escalated=None)
    report = build_project_payload(tmp_path, "red")
    assert report["observed_level"] == "L0"
    assert report["components"]["demonstrated_evidence"] == 0.0


def test_overview_sorts_weakest_first(tmp_path: Path) -> None:
    strong = tmp_path / "strong"
    weak = tmp_path / "weak"
    strong.mkdir()
    weak.mkdir()
    _seed_gates(strong)
    _seed_run(strong, 0, level="L1", sublevel="L1.1", ok=True, escalated=False)
    scan = {
        "children": [
            {"name": "strong", "path": str(strong), "is_git": True},
            {"name": "weak", "path": str(weak), "is_git": True},
            {"name": "not-git", "path": str(tmp_path), "is_git": False},
        ]
    }
    out = build_overview_payload(tmp_path, scan)
    assert out["ok"] is True
    assert out["count"] == 2
    assert [r["project"] for r in out["projects"]] == ["weak", "strong"]
    assert out["projects"][1]["claim"] == "L1.1b in strong"
