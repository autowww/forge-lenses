"""Tests for Copilot intent classification."""

from __future__ import annotations

import pytest

from lenses.sdlc_copilot.intent import classify_copilot_strategy, map_reduce_enabled


def _scan(git_names: list[str]) -> dict:
    return {
        "children": [{"name": n, "is_git": True} for n in git_names],
        "resolved_at": None,
    }


def test_portfolio_each_project_on_projects_route() -> None:
    s = classify_copilot_strategy(
        "can you describe each project in the workspace 1 sentence",
        studio_route="projects",
        scan_state=_scan(["a", "b", "c"]),
    )
    assert s == "portfolio_map_reduce"


def test_single_shot_narrow_question() -> None:
    s = classify_copilot_strategy(
        "what is forge-lenses?",
        studio_route="overview",
        scan_state=_scan(["forge-lenses"]),
    )
    assert s == "single_shot"


def test_map_reduce_enabled_default_for_large_portfolio(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("LENSES_COPILOT_MAP_REDUCE", raising=False)
    assert map_reduce_enabled("portfolio_map_reduce", 12) is True
    assert map_reduce_enabled("portfolio_map_reduce", 5) is False


def test_map_reduce_disabled_by_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LENSES_COPILOT_MAP_REDUCE", "0")
    assert map_reduce_enabled("portfolio_map_reduce", 20) is False
