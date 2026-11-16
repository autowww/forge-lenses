"""HTTP contract tests for ``/api/bridge/*`` (Sprint B1)."""

from __future__ import annotations

import json
import threading
from http.client import HTTPConnection
from pathlib import Path

import pytest

from lenses.auth_session import SessionManager
from lenses.serve import LensesHandler


@pytest.fixture
def bridge_http_server(tmp_path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("LENSES_EXPERIMENTAL_ORCHESTRATION_GRAPH", "1")
    monkeypatch.setenv("LENSES_EXPERIMENTAL_BRIDGE_SPINE", "1")
    monkeypatch.setenv("LENSES_ORCHESTRATION_AUTO_SEED", "0")
    wr = tmp_path.resolve()
    (wr / ".lenses-local").mkdir(parents=True)
    from lenses.orchestration_graph.db import connect
    from lenses.orchestration_graph.seed_demo import apply_demo_bundle

    fixture = Path(__file__).resolve().parent.parent / "lenses" / "fixtures" / "orchestration-graph.demo.json"
    bundle = json.loads(fixture.read_text(encoding="utf-8"))
    conn = connect(wr)
    assert conn is not None
    apply_demo_bundle(conn, bundle)
    conn.close()

    LensesHandler.workspace_root = wr
    LensesHandler.registry = {}
    LensesHandler.expected_github_login = None
    LensesHandler.session_manager = SessionManager(wr)
    from http.server import ThreadingHTTPServer

    server = ThreadingHTTPServer(("127.0.0.1", 0), LensesHandler)
    port = server.server_address[1]
    th = threading.Thread(target=server.serve_forever, daemon=True)
    th.start()
    try:
        yield port
    finally:
        server.shutdown()
        server.server_close()
        th.join(timeout=10)


def _get_json(port: int, path: str) -> tuple[int, dict]:
    c = HTTPConnection("127.0.0.1", port)
    c.request("GET", path)
    resp = c.getresponse()
    raw = resp.read().decode("utf-8")
    c.close()
    try:
        body = json.loads(raw) if raw else {}
    except json.JSONDecodeError:
        body = {"_raw": raw}
    return resp.status, body if isinstance(body, dict) else {}


def test_bridge_registry_and_terms_http(bridge_http_server: int) -> None:
    port = bridge_http_server
    st, reg = _get_json(port, "/api/bridge/registry")
    assert st == 200
    assert reg.get("ok") is True
    assert isinstance(reg.get("registry"), dict)
    assert reg["registry"].get("registry_version")

    st2, terms = _get_json(port, "/api/bridge/registry/terms/work_unit")
    assert st2 == 200
    assert terms.get("ok") is True
    assert terms.get("neutral_entry") is not None


def test_bridge_trace_projections_neighbors_provenance_http(bridge_http_server: int) -> None:
    port = bridge_http_server
    sid = "ogs%3Ademo%3Astory%3Arate-limit-auth"
    st, tr = _get_json(port, f"/api/bridge/trace/{sid}?max_depth=4&max_nodes=120")
    assert st == 200
    assert tr.get("ok") is True
    nodes = tr.get("nodes") or []
    assert nodes
    assert all("spine_meta" in n for n in nodes)
    assert tr.get("bridge", {}).get("traceability_score", {}).get("ok") is True

    stp, pr = _get_json(port, f"/api/bridge/projections/{sid}?lens=forge")
    assert stp == 200
    assert pr.get("ok") is True
    assert pr.get("spine_meta", {}).get("created_at")

    stn, nb = _get_json(port, f"/api/bridge/neighbors/{sid}")
    assert stn == 200
    assert nb.get("ok") is True
    assert isinstance(nb.get("outgoing_edges"), list)
    assert isinstance(nb.get("incoming_edges"), list)

    stpv, pv = _get_json(port, f"/api/bridge/provenance/{sid}?max_depth=3&max_nodes=80")
    assert stpv == 200
    assert pv.get("ok") is True
    assert (pv.get("bridge") or {}).get("direction") == "upstream_provenance"
