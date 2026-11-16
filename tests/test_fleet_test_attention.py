"""Workspace scan merge for Forge Fleet Test Fleet attention file."""

from __future__ import annotations

import json
from pathlib import Path

from lenses.scan import attach_fleet_test_attention, scan_workspace
from lenses.registry import load_registry


def test_attach_fleet_test_attention(tmp_path: Path) -> None:
    d = tmp_path / ".lenses-local"
    d.mkdir(parents=True)
    payload = {
        "ok": True,
        "headline": "Fleet test: 5 host CPU probe(s) — median 12.0%",
        "batch_id": "abc",
        "to": "/settings/fleet",
    }
    (d / "fleet-test-attention.json").write_text(json.dumps(payload), encoding="utf-8")
    reg = load_registry(tmp_path)
    state = scan_workspace(tmp_path, tmp_path, reg, git_extended=False)
    attach_fleet_test_attention(tmp_path, state)
    fta = state.get("fleet_test_attention")
    assert isinstance(fta, dict)
    assert fta.get("headline") == payload["headline"]
