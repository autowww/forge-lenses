"""Tests for delivery signal aggregation and fixtures."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from lenses.delivery_signals.aggregate import build_delivery_overview_payload
from lenses.delivery_signals.feature_flag import experimental_delivery_signals_enabled
from lenses.delivery_signals.local_signals_store import read_local_delivery_signals


def _minimal_scan(children: list[dict]) -> dict:
    return {
        "resolved_at": "2026-04-11T12:00:00+00:00",
        "children": children,
    }


def test_disabled_payload_summarizes_workspace(tmp_path: Path) -> None:
    scan = _minimal_scan(
        [
            {"name": "alpha", "is_git": True, "git": {"head_short": "abc"}},
            {"name": "beta", "is_git": False, "git": {}},
        ]
    )
    out = build_delivery_overview_payload(
        workspace_root=tmp_path,
        scan_state=scan,
        force_flag=False,
    )
    assert out["ok"] is True
    assert out["feature_enabled"] is False
    assert out["provider_kind"] == "disabled"
    assert out["workspace_summary"]["child_count"] == 2
    assert out["workspace_summary"]["git_repo_count"] == 1
    assert out["repos"] == []
    assert any("off" in h.lower() for h in out["hints"])


def test_enabled_scan_only_hints(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("LENSES_DELIVERY_SIGNALS_SEED_DEMO", raising=False)
    scan = _minimal_scan([{"name": "solo", "is_git": True, "git": {"branch": "main"}}])
    out = build_delivery_overview_payload(
        workspace_root=tmp_path,
        scan_state=scan,
        force_flag=True,
    )
    assert out["feature_enabled"] is True
    assert out["provider_kind"] == "scan_only"
    assert len(out["repos"]) == 1
    assert out["repos"][0]["project"] == "solo"
    assert out["repos"][0]["data_sources"] == ["workspace_scan"]
    assert out["repos"][0]["workflows"] == []
    assert any("delivery-signals.json" in h for h in out["hints"])


def test_local_fixture_merges(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("LENSES_DELIVERY_SIGNALS_SEED_DEMO", raising=False)
    local = tmp_path / ".lenses-local"
    local.mkdir(parents=True)
    (local / "delivery-signals.json").write_text(
        json.dumps(
            {
                "schema_version": 1,
                "repos": {
                    "solo": {
                        "ci_provider": "jenkins",
                        "workflows": [{"name": "build", "status": "running"}],
                        "trace_links": [{"kind": "pr", "label": "PR 1", "url": "https://x"}],
                    }
                },
            }
        ),
        encoding="utf-8",
    )
    scan = _minimal_scan([{"name": "solo", "is_git": True, "git": {}}])
    out = build_delivery_overview_payload(
        workspace_root=tmp_path,
        scan_state=scan,
        force_flag=True,
    )
    assert out["provider_kind"] == "local_fixture"
    row = out["repos"][0]
    assert "local_fixture" in row["data_sources"]
    assert row["ci_provider"] == "jenkins"
    assert len(row["workflows"]) == 1
    assert row["workflows"][0]["name"] == "build"


def test_seed_demo_env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LENSES_DELIVERY_SIGNALS_SEED_DEMO", "1")
    scan = _minimal_scan([{"name": "forgesdlc", "is_git": True, "git": {}}])
    out = build_delivery_overview_payload(
        workspace_root=tmp_path,
        scan_state=scan,
        force_flag=True,
    )
    assert out["provider_kind"] == "local_fixture"
    row = out["repos"][0]
    assert row["project"] == "forgesdlc"
    assert row["workflows"]


def test_read_local_delivery_signals_invalid_returns_none(tmp_path: Path) -> None:
    local = tmp_path / ".lenses-local"
    local.mkdir(parents=True)
    (local / "delivery-signals.json").write_text("{not json", encoding="utf-8")
    assert read_local_delivery_signals(tmp_path) is None


def test_feature_flag_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("LENSES_EXPERIMENTAL_DELIVERY_SIGNALS", raising=False)
    assert experimental_delivery_signals_enabled() is True
    monkeypatch.setenv("LENSES_EXPERIMENTAL_DELIVERY_SIGNALS", "0")
    assert experimental_delivery_signals_enabled() is False
