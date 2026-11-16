"""Tests for Docs Health git branch policy resolver."""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from lenses.docs_health.git_branch_policy import GitBranchPolicy, resolve_git_branch_policy


def test_fallback_team_tier_feature_prefixed() -> None:
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        (root / ".git").mkdir()
        p = resolve_git_branch_policy(root)
        assert p.trunk == "main"
        assert p.style == "feature_prefixed"
        assert p.source == "fallback_team_tier"
        assert p.format_docs_health_branch("a" * 16) == "feature/docs-health-aaaaaaaaaa"


def test_branching_yml_legacy() -> None:
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        (root / ".git").mkdir()
        (root / "forge").mkdir()
        (root / "forge" / "branching.yml").write_text(
            "trunk: main\ndocs_health_branch_style: legacy\n",
            encoding="utf-8",
        )
        p = resolve_git_branch_policy(root)
        assert p.style == "legacy_docs_health"
        assert p.format_docs_health_branch("b" * 12) == "docs-health/bbbbbbbbbb"


def test_embedded_blueprints_strategy() -> None:
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        (root / ".git").mkdir()
        bp = root / "blueprints" / "sdlc" / "methodologies" / "forge" / "setup"
        bp.mkdir(parents=True)
        (bp / "BRANCHING-STRATEGY.md").write_text("# branching\n", encoding="utf-8")
        p = resolve_git_branch_policy(root)
        assert "blueprints" in p.source
        assert p.style == "feature_prefixed"


def test_workspace_level_blueprints(tmp_path: Path) -> None:
    proj = tmp_path / "proj"
    proj.mkdir()
    (proj / ".git").mkdir()
    ws = tmp_path
    bp = ws / "blueprints" / "sdlc" / "methodologies" / "forge" / "setup"
    bp.mkdir(parents=True)
    (bp / "BRANCHING-STRATEGY.md").write_text("# x\n", encoding="utf-8")
    p = resolve_git_branch_policy(proj, workspace_root=ws)
    assert p.source.startswith("workspace/blueprints")
