"""Cross-team release orchestration (Sprint 7)."""

from __future__ import annotations

from pathlib import Path

import pytest

from lenses.cross_team_release.aggregate import build_cross_team_release_overview
from lenses.cross_team_release.feature_flag import experimental_cross_team_release_enabled


def test_cross_team_release_disabled(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("LENSES_EXPERIMENTAL_CROSS_TEAM_RELEASE", "0")
    assert experimental_cross_team_release_enabled() is False
    scan = {"children": [], "resolved_at": "t"}
    out = build_cross_team_release_overview(workspace_root=tmp_path, scan_state=scan, force_flag=False)
    assert out["feature_enabled"] is False


def test_cross_team_release_demo_packet(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.delenv("LENSES_EXPERIMENTAL_CROSS_TEAM_RELEASE", raising=False)
    monkeypatch.setenv("LENSES_CROSS_TEAM_RELEASE_SEED_DEMO", "1")
    monkeypatch.setenv("LENSES_CICD_ORCHESTRATION_SEED_DEMO", "1")
    monkeypatch.setenv("LENSES_TEST_QUALITY_SEED_DEMO", "1")
    monkeypatch.setenv("LENSES_DEVSECOPS_COMPLIANCE_SEED_DEMO", "1")
    scan = {"children": [{"name": "forgesdlc", "is_git": True}], "resolved_at": "t"}
    out = build_cross_team_release_overview(workspace_root=tmp_path, scan_state=scan, force_flag=True)
    assert out["feature_enabled"] is True
    assert out["provider_kind"] == "local_fixture"
    assert len(out.get("change_requests") or []) >= 1
    board = out.get("dependency_board") or {}
    assert len(board.get("nodes") or []) >= 1
    assert len(board.get("edges") or []) >= 1
    cal = out.get("release_calendar") or {}
    assert len(cal.get("events") or []) >= 1
    pkt = out.get("go_no_go_packet") or {}
    md = str(pkt.get("markdown") or "")
    assert "What ships" in md or "Release train" in md
    assert "What blocks it" in md
    assert "CHG-2026-0411" in md or any(
        "CHG-2026-0411" in str(s.get("body_md", "")) for s in (pkt.get("sections") or []) if isinstance(s, dict)
    )
    comm = out.get("communication_artifacts") or {}
    assert len(str(comm.get("blocker_summary_md") or "")) > 10
    live = out.get("live_enrichment") or {}
    assert isinstance(live.get("blocked_promotions"), list)
