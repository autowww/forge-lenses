"""Nested roadmap config API (FLS4-001)."""

from __future__ import annotations

from lenses.nested_roadmap_workspace import build_nested_roadmap_config_from_workspace


def test_build_nested_roadmap_config_empty_state(tmp_path):
    ws = tmp_path
    state = {"roadmaps": [], "wbs": []}
    cfg = build_nested_roadmap_config_from_workspace(ws, state, repo_filter="all", roadmap_focus="")
    assert cfg["version"] == 1
    assert "columns" in cfg
    assert "bars" in cfg
