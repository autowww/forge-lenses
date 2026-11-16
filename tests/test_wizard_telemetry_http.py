"""HTTP integration tests: POST /api/blueprints/wizard/telemetry via LensesHandler."""

from __future__ import annotations

import json
import threading
from http.client import HTTPConnection
from http.server import ThreadingHTTPServer
from pathlib import Path

import pytest

from lenses.auth_session import SessionManager
from lenses.serve import LensesHandler


@pytest.fixture
def lenses_http_server(tmp_path, monkeypatch: pytest.MonkeyPatch):
    wr = tmp_path.resolve()
    LensesHandler.workspace_root = wr
    LensesHandler.registry = {}
    LensesHandler.expected_github_login = None
    LensesHandler.session_manager = SessionManager(wr)
    server = ThreadingHTTPServer(("127.0.0.1", 0), LensesHandler)
    port = server.server_address[1]
    th = threading.Thread(target=server.serve_forever, daemon=True)
    th.start()
    try:
        yield wr, port
    finally:
        server.shutdown()
        server.server_close()
        th.join(timeout=10)


def test_http_post_telemetry_persists_via_serve(
    lenses_http_server: tuple[Path, int], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("LENSES_EXPERIMENTAL_BLUEPRINTS_WIZARD", "1")
    monkeypatch.setenv("LENSES_BLUEPRINTS_WIZARD_TELEMETRY", "1")
    wr, port = lenses_http_server

    body = json.dumps(
        {
            "event": "step_view",
            "session_id": "http_test_sess",
            "step_index": 2,
            "mission_mode": "explore",
        }
    ).encode("utf-8")

    conn = HTTPConnection("127.0.0.1", port)
    conn.request(
        "POST",
        "/api/blueprints/wizard/telemetry",
        body=body,
        headers={"Content-Type": "application/json"},
    )
    resp = conn.getresponse()
    assert resp.status == 200
    out = json.loads(resp.read().decode("utf-8"))
    conn.close()

    assert out.get("ok") is True

    p = wr / ".lenses-local" / "blueprints-wizard" / "telemetry.jsonl"
    assert p.is_file()
    line = p.read_text(encoding="utf-8").strip().split("\n")[-1]
    row = json.loads(line)
    assert row.get("kind") == "client"
    assert row.get("event") == "step_view"
    assert row.get("session_id") == "http_test_sess"


def test_http_post_telemetry_400_when_telemetry_env_off(
    lenses_http_server: tuple[Path, int], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("LENSES_EXPERIMENTAL_BLUEPRINTS_WIZARD", "1")
    monkeypatch.delenv("LENSES_BLUEPRINTS_WIZARD_TELEMETRY", raising=False)
    wr, port = lenses_http_server

    body = json.dumps({"event": "step_view", "session_id": "x"}).encode("utf-8")
    conn = HTTPConnection("127.0.0.1", port)
    conn.request(
        "POST",
        "/api/blueprints/wizard/telemetry",
        body=body,
        headers={"Content-Type": "application/json"},
    )
    resp = conn.getresponse()
    assert resp.status == 400
    out = json.loads(resp.read().decode("utf-8"))
    conn.close()

    assert out.get("ok") is False
