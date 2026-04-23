"""Sprint B5: handoff package, export renderers, return ingestion, APIs."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
FIXTURE = ROOT / "lenses" / "fixtures" / "orchestration-graph.demo.json"


@pytest.fixture
def seeded_workspace(tmp_path, monkeypatch):
    monkeypatch.setenv("LENSES_EXPERIMENTAL_ORCHESTRATION_GRAPH", "1")
    monkeypatch.setenv("LENSES_EXPERIMENTAL_HANDOFF_BRIDGE_B5", "1")
    monkeypatch.setenv("LENSES_ORCHESTRATION_AUTO_SEED", "0")
    ws = tmp_path / "workspace"
    ws.mkdir()
    (ws / ".lenses-local").mkdir(parents=True)
    from lenses.orchestration_graph.db import connect
    from lenses.orchestration_graph.seed_demo import apply_demo_bundle

    conn = connect(ws)
    assert conn is not None
    apply_demo_bundle(conn, json.loads(FIXTURE.read_text(encoding="utf-8")))
    try:
        yield ws, conn
    finally:
        conn.close()


def test_export_renders_cursor_vs_claude_distinct(seeded_workspace, monkeypatch) -> None:
    monkeypatch.setenv("LENSES_EXPERIMENTAL_HANDOFF_BRIDGE_B5", "1")
    _, conn = seeded_workspace
    from lenses.bridge.handoff_service import export_handoff

    base = export_handoff(conn, "ogs:demo:b5:pkg:auth-rate", {})
    assert base.get("ok") is True
    ex = base.get("exports") or {}
    c = export_handoff(conn, "ogs:demo:b5:pkg:auth-rate", {"target_key": "claude"})
    ex2 = c.get("exports") or {}
    assert "Claude" in (ex2.get("markdown_pack") or "") or "claude" in (ex2.get("json_manifest") or "").lower()
    assert ex.get("markdown_pack") != ex2.get("markdown_pack")


def test_demo_gaps_show_missing_acceptance_and_review_pack(seeded_workspace, monkeypatch) -> None:
    monkeypatch.setenv("LENSES_EXPERIMENTAL_HANDOFF_BRIDGE_B5", "1")
    _, conn = seeded_workspace
    from lenses.bridge.handoff_service import handoff_gaps

    g = handoff_gaps(conn, "ogs:demo:b5:pkg:auth-rate")
    assert g.get("ok") is True
    assert "security_review_complete" in (g.get("missing_acceptance") or [])
    assert "review_pack_link" in (g.get("missing_evidence") or [])


def test_return_ingest_idempotent(seeded_workspace, monkeypatch) -> None:
    monkeypatch.setenv("LENSES_EXPERIMENTAL_HANDOFF_BRIDGE_B5", "1")
    ws, conn = seeded_workspace
    from lenses.bridge.handoff_service import create_handoff_package, ingest_return

    r = create_handoff_package(
        conn,
        {
            "title": "Idempotent test",
            "target_key": "cursor",
            "objective": "test",
            "work_unit_graph_ids": ["ogs:demo:story:rate-limit-auth"],
            "acceptance_criteria": ["a1"],
            "launch_pack_version": "v-test",
        },
    )
    assert r.get("ok") is True
    pid = str(r["id"])
    body = {
        "ingest_fingerprint": "fp-test-unique-1",
        "branch_name": "b1",
        "partial_return": True,
        "satisfied_acceptance_keys": [],
    }
    a = ingest_return(conn, pid, body)
    assert a.get("ok") and not a.get("duplicate")
    b = ingest_return(conn, pid, {**body, "execution_session_id": a.get("session_id")})
    assert b.get("duplicate") is True


def test_partial_return_flags(seeded_workspace, monkeypatch) -> None:
    monkeypatch.setenv("LENSES_EXPERIMENTAL_HANDOFF_BRIDGE_B5", "1")
    _, conn = seeded_workspace
    from lenses.bridge.handoff_service import handoff_status
    from lenses.orchestration_graph.query import fetch_entity

    st = handoff_status(conn, "ogs:demo:b5:pkg:auth-rate")
    assert st.get("ok") is True
    lr = st.get("latest_execution_return")
    assert lr and fetch_entity(conn, str(lr.get("id")))


def test_http_get_enabled_and_gaps(seeded_workspace, monkeypatch) -> None:
    monkeypatch.setenv("LENSES_EXPERIMENTAL_HANDOFF_BRIDGE_B5", "1")
    ws, _ = seeded_workspace
    import urllib.parse

    from lenses.bridge.handoff_http import handle_handoff_b5_get

    got: list[tuple[int, dict]] = []

    def send_json(code: int, d: dict) -> None:
        got.append((code, d))

    assert handle_handoff_b5_get(
        workspace_root=ws,
        path="/api/handoffs/enabled",
        parsed=urllib.parse.urlparse("/api/handoffs/enabled"),
        send_json=send_json,
    )
    assert got[-1][0] == 200
    assert got[-1][1].get("enabled") is True

    assert handle_handoff_b5_get(
        workspace_root=ws,
        path="/api/handoffs/ogs:demo:b5:pkg:auth-rate/gaps",
        parsed=urllib.parse.urlparse("/api/handoffs/x/gaps"),
        send_json=send_json,
    )
    assert got[-1][1].get("missing_acceptance")


def test_integration_work_item_to_handoff_summary(seeded_workspace, monkeypatch) -> None:
    monkeypatch.setenv("LENSES_EXPERIMENTAL_HANDOFF_BRIDGE_B5", "1")
    _, conn = seeded_workspace
    from lenses.bridge.handoff_service import handoff_summary_for_work_item, list_handoff_packages_for_work_item

    assert "ogs:demo:b5:pkg:auth-rate" in list_handoff_packages_for_work_item(conn, "S-1842")
    assert "ogs:demo:b5:pkg:auth-rate" in list_handoff_packages_for_work_item(conn, "ogs:demo:story:rate-limit-auth")
    s = handoff_summary_for_work_item(conn, "S-1842")
    assert s and s.get("handoff_packages")
