"""Foundry stub endpoints."""

from __future__ import annotations

from pathlib import Path

import pytest


@pytest.fixture
def ws(tmp_path, monkeypatch):
    monkeypatch.setenv("LENSES_EXPERIMENTAL_ORCHESTRATION_GRAPH", "1")
    monkeypatch.setenv("LENSES_EXPERIMENTAL_AGENTIC_BRIDGE_B3", "1")
    ws = tmp_path / "workspace"
    ws.mkdir()
    return ws


def test_campaigns_501(ws: Path):
    from lenses.foundry.http import handle_foundry_post

    out: dict = {}

    def send(code, payload):
        out["code"] = code
        out["payload"] = payload

    handle_foundry_post(
        workspace_root=ws,
        post_path="/api/foundry/campaigns",
        body={},
        send_json=send,
        may_run_actions=lambda _ip: True,
        client_ip="127.0.0.1",
    )
    assert out["code"] == 501
    assert out["payload"]["reason"] == "dark_factory_level_not_wired"
