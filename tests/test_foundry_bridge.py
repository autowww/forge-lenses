"""Foundry bridge — payload, store, HTTP discovery."""

from __future__ import annotations

from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
SAMPLE_RUN = ROOT / "tests" / "fixtures" / "foundry" / "sample-run"


@pytest.fixture
def foundry_ws(tmp_path, monkeypatch):
    monkeypatch.setenv("LENSES_EXPERIMENTAL_ORCHESTRATION_GRAPH", "1")
    monkeypatch.setenv("LENSES_EXPERIMENTAL_AGENTIC_BRIDGE_B3", "1")
    monkeypatch.setenv("LENSES_EXPERIMENTAL_FOUNDRY", "1")
    ws = tmp_path / "workspace"
    ws.mkdir()
    target = ws / "forge-df-test-project"
    target.mkdir()
    (target / "src" / "dfcalc").mkdir(parents=True)
    (target / "src" / "dfcalc" / "engine.py").write_text("def multiply(a,b): return a+b\n", encoding="utf-8")
    (target / "tests").mkdir()
    (target / "fixtures").mkdir()
    (target / "fixtures" / "multiply_fix.json").write_text("{}", encoding="utf-8")
    return ws


def test_foundry_enabled(monkeypatch):
    from lenses.foundry.feature import foundry_enabled

    monkeypatch.setenv("LENSES_EXPERIMENTAL_ORCHESTRATION_GRAPH", "1")
    monkeypatch.setenv("LENSES_EXPERIMENTAL_AGENTIC_BRIDGE_B3", "1")
    assert foundry_enabled() is True
    monkeypatch.setenv("LENSES_EXPERIMENTAL_FOUNDRY", "0")
    assert foundry_enabled() is False


def test_normalize_run_dir():
    from lenses.foundry.payload import normalize_run_dir

    out = normalize_run_dir(SAMPLE_RUN)
    assert out["final_status"] == "pass"
    assert out["assay_ok"] is True
    phases = out["phases"]
    assert any(p["id"] == "classify" and p["status"] == "completed" for p in phases)


def test_capabilities_payload():
    from lenses.foundry.payload import capabilities_payload

    cap = capabilities_payload()
    assert cap["ladder"]["L1"]["status"] == "available"
    assert cap["ladder"]["L2"]["status"] == "stub"


def test_store_roundtrip(foundry_ws: Path):
    from lenses.foundry.store import create_run_record, load_run, save_run

    rec = create_run_record(goal="g", target="/t", level="L1", execution_mode="draft")
    save_run(foundry_ws, rec)
    loaded = load_run(foundry_ws, rec["id"])
    assert loaded is not None
    assert loaded["goal"] == "g"


def test_http_enabled_get(foundry_ws: Path):
    from lenses.foundry.http import handle_foundry_get

    out: dict = {}

    def send(code, payload):
        out["code"] = code
        out["payload"] = payload

    assert handle_foundry_get(workspace_root=foundry_ws, path="/api/foundry/enabled", send_json=send)
    assert out["payload"]["enabled"] is True
