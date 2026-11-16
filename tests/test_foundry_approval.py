"""Foundry approval and promote gates."""

from __future__ import annotations

from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
SAMPLE_RUN = ROOT / "tests" / "fixtures" / "foundry" / "sample-run"


@pytest.fixture
def ws(tmp_path, monkeypatch):
    monkeypatch.setenv("LENSES_EXPERIMENTAL_ORCHESTRATION_GRAPH", "1")
    monkeypatch.setenv("LENSES_EXPERIMENTAL_AGENTIC_BRIDGE_B3", "1")
    ws = tmp_path / "workspace"
    ws.mkdir()
    target = ws / "live"
    target.mkdir()
    (target / "src" / "dfcalc").mkdir(parents=True)
    (target / "src" / "dfcalc" / "engine.py").write_text("old\n", encoding="utf-8")
    worktree = SAMPLE_RUN / "worktree"
    (worktree / "src" / "dfcalc").mkdir(parents=True, exist_ok=True)
    (worktree / "src" / "dfcalc" / "engine.py").write_text("new\n", encoding="utf-8")
    from lenses.foundry.store import create_run_record, save_run, touch_run

    rec = create_run_record(
        goal="g",
        target=str(target),
        level="L1",
        execution_mode="draft",
    )
    rec = touch_run(
        rec,
        status="completed",
        assay_ok=True,
        foundry_run_dir=str(SAMPLE_RUN),
        final_status="pass",
    )
    save_run(ws, rec)
    return ws, rec["id"]


def test_approve_requires_confirm(ws):
    workspace, rid = ws
    from lenses.foundry.http import handle_foundry_post

    out: dict = {}

    def send(code, payload):
        out["code"] = code
        out["payload"] = payload

    handle_foundry_post(
        workspace_root=workspace,
        post_path=f"/api/foundry/runs/{rid}/approve",
        body={},
        send_json=send,
        may_run_actions=lambda _ip: True,
        client_ip="127.0.0.1",
    )
    assert out["code"] == 400
    assert out["payload"]["error"] == "confirm_human_approval_required"


def test_approve_promotes(ws):
    workspace, rid = ws
    from lenses.foundry.http import handle_foundry_post
    from lenses.foundry.store import load_run

    out: dict = {}

    def send(code, payload):
        out["code"] = code
        out["payload"] = payload

    handle_foundry_post(
        workspace_root=workspace,
        post_path=f"/api/foundry/runs/{rid}/approve",
        body={"confirm_human_approval": True},
        send_json=send,
        may_run_actions=lambda _ip: True,
        client_ip="127.0.0.1",
    )
    assert out["code"] == 200
    rec = load_run(workspace, rid)
    assert rec is not None
    assert rec.get("promoted") is True
    live = Path(rec["target"]) / "src" / "dfcalc" / "engine.py"
    assert live.read_text(encoding="utf-8") == "new\n"
