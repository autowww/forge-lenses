"""Tests for Copilot map-reduce planner."""

from __future__ import annotations

from pathlib import Path

from lenses.sdlc_copilot.planner import build_portfolio_plan


def test_portfolio_plan_one_subtask_per_repo(tmp_path: Path) -> None:
    scan = {
        "children": [
            {"name": "alpha", "is_git": True},
            {"name": "beta", "is_git": True},
            {"name": "notes", "is_git": False},
        ],
        "resolved_at": None,
    }
    plan = build_portfolio_plan(
        workspace_root=tmp_path,
        user_message="describe each project in one sentence",
        scan_state=scan,
        include_folders=False,
    )
    assert plan.strategy == "portfolio_map_reduce"
    assert len(plan.subtasks) == 2
    assert plan.subtasks[0].scope_site == "alpha"
    assert plan.subtasks[1].scope_site == "beta"
    assert "alpha" in plan.subtasks[0].fts_query


def test_portfolio_plan_includes_charge_md_when_present(tmp_path: Path) -> None:
    repo = tmp_path / "demo" / "forge"
    repo.mkdir(parents=True)
    (repo / "charge.md").write_text("# Charge\nDemo repo.\n", encoding="utf-8")
    scan = {"children": [{"name": "demo", "is_git": True}], "resolved_at": None}
    plan = build_portfolio_plan(
        workspace_root=tmp_path,
        user_message="summarize each repo",
        scan_state=scan,
    )
    assert plan.subtasks[0].related_md_rel_paths == ["demo/forge/charge.md"]
