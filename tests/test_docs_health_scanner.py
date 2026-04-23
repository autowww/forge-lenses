"""Tests for deterministic Docs Health scanner."""

from __future__ import annotations

from pathlib import Path

from lenses.docs_health.contract import resolve_project_docs_contract
from lenses.docs_health.scanner import run_deterministic_scan


def test_scan_detects_missing_readme_section(tmp_path: Path) -> None:
    (tmp_path / "README.md").write_text("# Demo\n\nHello\n", encoding="utf-8")
    contract = resolve_project_docs_contract(tmp_path, project_slug="demo")
    out = run_deterministic_scan(tmp_path, contract)
    assert out["ok"] is True
    titles = {f["title"] for f in out["findings"]}
    assert any("Overview" in t for t in titles)


def test_scan_detects_broken_relative_link(tmp_path: Path) -> None:
    (tmp_path / "README.md").write_text("# X\n\n[broken](./missing.md)\n", encoding="utf-8")
    contract = resolve_project_docs_contract(tmp_path, project_slug="demo")
    contract["require_adr"] = False
    contract["require_release_note"] = False
    contract["require_architecture_diagram"] = False
    contract["readme_required_sections"] = []
    out = run_deterministic_scan(tmp_path, contract)
    cats = {f["category"] for f in out["findings"]}
    assert "link_integrity" in cats


def test_clusters_group_findings(tmp_path: Path) -> None:
    (tmp_path / "README.md").write_text("# X\n\nTODO fix\n", encoding="utf-8")
    contract = resolve_project_docs_contract(tmp_path, project_slug="demo")
    contract["require_adr"] = False
    contract["require_release_note"] = False
    contract["require_architecture_diagram"] = False
    contract["readme_required_sections"] = []
    out = run_deterministic_scan(tmp_path, contract)
    assert out["clusters"]
    assert len(out["clusters"]) >= 1


def test_score_includes_sub_scores_and_potential_delta(tmp_path: Path) -> None:
    (tmp_path / "README.md").write_text("# X\n\nBody.\n", encoding="utf-8")
    contract = resolve_project_docs_contract(tmp_path, project_slug="demo")
    contract["require_adr"] = False
    contract["require_release_note"] = False
    contract["require_architecture_diagram"] = False
    contract["readme_required_sections"] = []
    out = run_deterministic_scan(tmp_path, contract)
    sc = out["score"]
    assert "sub_scores" in sc
    assert "weights" in sc
    assert "formula" in sc
    assert isinstance(sc.get("potential_delta_if_resolved"), int)
    assert sc["potential_delta_if_resolved"] >= 0
    if out["findings"]:
        f0 = out["findings"][0]
        assert "expected_score_impact" in f0
        assert "scope" in f0


def test_scope_drift_module_path(tmp_path: Path) -> None:
    (tmp_path / "README.md").write_text("# X\n\n## Overview\n\nok\n## Getting started\n\nok\n", encoding="utf-8")
    contract = resolve_project_docs_contract(tmp_path, project_slug="demo")
    contract["require_adr"] = False
    contract["require_release_note"] = False
    contract["require_architecture_diagram"] = False
    contract["readme_required_sections"] = []
    contract["scope"] = {"repository": "demo", "module_paths": ["no-such-module"]}
    out = run_deterministic_scan(tmp_path, contract)
    cats = {f["category"] for f in out["findings"]}
    assert "scope_drift" in cats
