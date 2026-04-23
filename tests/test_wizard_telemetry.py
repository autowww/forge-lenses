"""Wizard telemetry JSONL (opt-in)."""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from lenses.blueprints_wizard import wizard_telemetry as wt


def test_wizard_telemetry_disabled_by_default(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.delenv("LENSES_BLUEPRINTS_WIZARD_TELEMETRY", raising=False)
    monkeypatch.setenv("LENSES_EXPERIMENTAL_BLUEPRINTS_WIZARD", "1")
    assert wt.wizard_telemetry_enabled() is False
    wt.append_event(tmp_path, {"ts": "x", "kind": "test"})
    p = tmp_path / ".lenses-local" / "blueprints-wizard" / "telemetry.jsonl"
    assert not p.is_file()


def test_ingest_client_event_when_enabled(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("LENSES_EXPERIMENTAL_BLUEPRINTS_WIZARD", "1")
    monkeypatch.setenv("LENSES_BLUEPRINTS_WIZARD_TELEMETRY", "1")
    assert wt.wizard_telemetry_enabled() is True
    out = wt.ingest_client_event(
        tmp_path,
        {"event": "step_view", "session_id": "abc12345", "step_index": 3, "mission_mode": "explore"},
    )
    assert out.get("ok") is True
    p = tmp_path / ".lenses-local" / "blueprints-wizard" / "telemetry.jsonl"
    assert p.is_file()
    line = p.read_text(encoding="utf-8").strip().split("\n")[-1]
    row = json.loads(line)
    assert row["kind"] == "client"
    assert row["event"] == "step_view"
    assert row["session_id"] == "abc12345"
    assert row["step_index"] == 3


def test_ingest_rejects_bad_event(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("LENSES_EXPERIMENTAL_BLUEPRINTS_WIZARD", "1")
    monkeypatch.setenv("LENSES_BLUEPRINTS_WIZARD_TELEMETRY", "1")
    out = wt.ingest_client_event(tmp_path, {"event": ""})
    assert out.get("ok") is False
