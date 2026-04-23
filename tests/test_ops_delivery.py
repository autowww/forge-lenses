"""Ops feedback loop and DORA-style metrics (Sprint 8)."""

from __future__ import annotations

from pathlib import Path

import pytest

from lenses.ops_delivery.aggregate import build_ops_delivery_overview
from lenses.ops_delivery.feature_flag import experimental_ops_delivery_enabled
from lenses.ops_delivery.ingest import expand_ingestions


def test_ops_delivery_disabled(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("LENSES_EXPERIMENTAL_OPS_DELIVERY", "0")
    assert experimental_ops_delivery_enabled() is False
    scan = {"children": [], "resolved_at": "t"}
    out = build_ops_delivery_overview(workspace_root=tmp_path, scan_state=scan, force_flag=False)
    assert out["feature_enabled"] is False


def test_ops_delivery_demo_dora_and_rollback(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.delenv("LENSES_EXPERIMENTAL_OPS_DELIVERY", raising=False)
    monkeypatch.setenv("LENSES_OPS_DELIVERY_SEED_DEMO", "1")
    monkeypatch.setenv("LENSES_CICD_ORCHESTRATION_SEED_DEMO", "1")
    monkeypatch.setenv("LENSES_TEST_QUALITY_SEED_DEMO", "1")
    scan = {"children": [{"name": "forgesdlc", "is_git": True}], "resolved_at": "t"}
    out = build_ops_delivery_overview(workspace_root=tmp_path, scan_state=scan, force_flag=True)
    assert out["feature_enabled"] is True
    assert out["provider_kind"] == "local_fixture"
    dm = out.get("dora_metrics") or {}
    assert "deployment_frequency" in dm
    assert (dm.get("deployment_frequency") or {}).get("production_successful_deploys", 0) >= 1
    assert dm.get("rework_signals") is not None
    incs = out.get("incidents") or []
    assert len(incs) >= 2
    assert any(str(i.get("incident_id")) == "PD-7788" for i in incs if isinstance(i, dict))
    traces = [i.get("traceability") for i in incs if isinstance(i, dict)]
    assert any(isinstance(t, dict) and t.get("release_version") for t in traces)
    rbs = out.get("rollback_signals") or []
    assert len(rbs) >= 1
    tpl = out.get("postmortem_templates") or []
    assert len(tpl) >= 1


def test_expand_ingestions_pagerduty() -> None:
    doc = {
        "incidents": [],
        "ingestions": [
            {
                "provider": "pagerduty",
                "payload": {
                    "id": "X1",
                    "title": "t",
                    "severity": "high",
                    "status": "open",
                    "created_at": "2026-04-11T10:00:00Z",
                    "custom_fields": {"story_ids": ["S-9"], "release_version": "1.0.0", "environment_id": "production"},
                },
            }
        ],
    }
    out = expand_ingestions(doc)
    ids = [i.get("incident_id") for i in out.get("incidents") or []]
    assert "X1" in ids
    row = next(i for i in out["incidents"] if i.get("incident_id") == "X1")
    assert "S-9" in (row.get("linked_story_ids") or [])
