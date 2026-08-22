"""Foundry run launch and polling."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

ROOT = Path(__file__).resolve().parent.parent
SAMPLE_RUN = ROOT / "tests" / "fixtures" / "foundry" / "sample-run"


@pytest.fixture
def ws(tmp_path, monkeypatch):
    monkeypatch.setenv("LENSES_EXPERIMENTAL_ORCHESTRATION_GRAPH", "1")
    monkeypatch.setenv("LENSES_EXPERIMENTAL_AGENTIC_BRIDGE_B3", "1")
    target = tmp_path / "workspace" / "proj"
    target.mkdir(parents=True)
    (target / "fixtures").mkdir()
    (target / "fixtures" / "multiply_fix.json").write_text("{}", encoding="utf-8")
    return tmp_path / "workspace"


def test_create_run_mocks_launcher(ws: Path):
    from lenses.foundry.http import handle_foundry_post
    from lenses.foundry.payload import normalize_run_dir
    from lenses.foundry.store import list_runs

    target = ws / "proj"
    normalized = normalize_run_dir(SAMPLE_RUN)

    def fake_launch(**kwargs):
        kwargs["on_complete"](normalized)

    out: dict = {}

    def send(code, payload):
        out["code"] = code
        out["payload"] = payload

    with patch("lenses.foundry.http.launch_run_async", side_effect=fake_launch):
        handle_foundry_post(
            workspace_root=ws,
            post_path="/api/foundry/runs",
            body={
                "goal": "fix failing multiply",
                "target": str(target),
                "level": "L1",
                "worker": "fake",
            },
            send_json=send,
            may_run_actions=lambda _ip: True,
            client_ip="127.0.0.1",
        )
    assert out["code"] == 201
    runs = list_runs(ws)
    assert len(runs) == 1
    assert runs[0]["status"] == "completed"
