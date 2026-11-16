"""Sprint B6: PDLC outcome bridge — launches, signals, learning, follow-on Ore, APIs."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
FIXTURE = ROOT / "lenses" / "fixtures" / "orchestration-graph.demo.json"


@pytest.fixture
def seeded_workspace(tmp_path, monkeypatch):
    monkeypatch.setenv("LENSES_EXPERIMENTAL_ORCHESTRATION_GRAPH", "1")
    monkeypatch.setenv("LENSES_EXPERIMENTAL_OUTCOME_BRIDGE_B6", "1")
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


def test_registry_loads() -> None:
    from lenses.bridge.pdlc_outcome_bridge_registry import load_pdlc_outcome_bridge_registry

    reg = load_pdlc_outcome_bridge_registry()
    assert reg.get("registry_version")
    assert reg.get("neutral_to_pdlc", {}).get("launch_record")


def test_demo_launch_bundle_links_release_signals_and_demand(seeded_workspace, monkeypatch) -> None:
    monkeypatch.setenv("LENSES_EXPERIMENTAL_OUTCOME_BRIDGE_B6", "1")
    _, conn = seeded_workspace
    from lenses.bridge.outcome_service import get_launch_bundle

    b = get_launch_bundle(conn, "ogs:demo:b6:launch:auth-train")
    assert b.get("ok") is True
    assert b.get("release_id") == "ogs:demo:release:v1.4.0"
    assert len(b.get("signals") or []) >= 8
    assert "ogs:demo:b6:learn:postv14" in (b.get("learning_summary_ids") or [])
    assert "ogs:demo:b6:ore:burst" in (b.get("followon_ore_ids") or [])
    assert "ogs:demo:b6:demand:burst" in (b.get("demand_signal_ids") or [])


def test_explain_scores_lists_reasons(seeded_workspace, monkeypatch) -> None:
    monkeypatch.setenv("LENSES_EXPERIMENTAL_OUTCOME_BRIDGE_B6", "1")
    _, conn = seeded_workspace
    from lenses.bridge.outcome_service import explain_scores_for_launch

    s = explain_scores_for_launch(conn, "ogs:demo:b6:launch:auth-train")
    assert s.get("ok") is True
    assert "launch_confidence" in s
    assert isinstance(s.get("explanations"), list) and len(s["explanations"]) >= 3


def test_create_followon_idempotent_for_demo_learning(seeded_workspace, monkeypatch) -> None:
    monkeypatch.setenv("LENSES_EXPERIMENTAL_OUTCOME_BRIDGE_B6", "1")
    _, conn = seeded_workspace
    from lenses.bridge.outcome_service import create_followon_ore

    a = create_followon_ore(
        conn,
        "ogs:demo:b6:learn:postv14",
        {"title": "x", "demand_title": "y"},
    )
    assert a.get("ok") is True
    assert a.get("idempotent") is True
    assert a.get("demand_signal_id") == "ogs:demo:b6:demand:burst"


def test_create_followon_idempotency_key(seeded_workspace, monkeypatch) -> None:
    monkeypatch.setenv("LENSES_EXPERIMENTAL_OUTCOME_BRIDGE_B6", "1")
    ws, conn = seeded_workspace
    from lenses.bridge.outcome_service import create_followon_ore
    from lenses.orchestration_graph.query import fetch_entity

    # Synthetic learning row
    from lenses.bridge.methodology_service import upsert_ogs_entity

    upsert_ogs_entity(
        conn,
        entity_id="ogs:test:b6:learn:1",
        kind="learning_summary",
        display_name="L",
        summary="s",
        payload={"source": "test", "freshness_at": "2026-04-01T00:00:00+00:00"},
        source_system="test",
        source_record_id="t1",
    )
    conn.commit()

    k = "idem-key-99"
    r1 = create_followon_ore(conn, "ogs:test:b6:learn:1", {"idempotency_key": k, "title": "Ore A"})
    assert r1.get("ok") and not r1.get("idempotent")
    dem = str(r1["demand_signal_id"])
    r2 = create_followon_ore(conn, "ogs:test:b6:learn:1", {"idempotency_key": k, "title": "Ore B"})
    assert r2.get("idempotent") is True
    assert r2.get("demand_signal_id") == dem
    assert fetch_entity(conn, dem) is not None


def test_trace_from_launch_includes_demand(seeded_workspace, monkeypatch) -> None:
    monkeypatch.setenv("LENSES_EXPERIMENTAL_OUTCOME_BRIDGE_B6", "1")
    _, conn = seeded_workspace
    from lenses.bridge.outcome_service import trace_outcome_entity

    t = trace_outcome_entity(conn, "ogs:demo:b6:launch:auth-train")
    assert t.get("ok") is True
    ids = {n["id"] for n in t.get("nodes") or []}
    assert "ogs:demo:b6:demand:burst" in ids
    assert "ogs:demo:story:rate-limit-auth" in ids


def test_pdlc_bridge_projection(seeded_workspace, monkeypatch) -> None:
    monkeypatch.setenv("LENSES_EXPERIMENTAL_OUTCOME_BRIDGE_B6", "1")
    _, conn = seeded_workspace
    from lenses.bridge.outcome_service import pdlc_bridge_for_entity

    p = pdlc_bridge_for_entity(conn, "ogs:demo:b6:launch:auth-train")
    assert p.get("ok") is True
    assert (p.get("projection") or {}).get("pdlc_stage_key") == "measure_learn"


def test_http_get_list_and_launch(seeded_workspace, monkeypatch) -> None:
    monkeypatch.setenv("LENSES_EXPERIMENTAL_OUTCOME_BRIDGE_B6", "1")
    ws, _ = seeded_workspace
    import urllib.parse

    from lenses.bridge.outcome_http import handle_outcome_b6_get

    got: list[tuple[int, dict]] = []

    def send_json(code: int, d: dict) -> None:
        got.append((code, d))

    assert handle_outcome_b6_get(
        workspace_root=ws,
        path="/api/outcomes/enabled",
        parsed=urllib.parse.urlparse("/api/outcomes/enabled"),
        send_json=send_json,
    )
    assert got[-1][1].get("enabled") is True

    assert handle_outcome_b6_get(
        workspace_root=ws,
        path="/api/launches/ogs:demo:b6:launch:auth-train",
        parsed=urllib.parse.urlparse("/x"),
        send_json=send_json,
    )
    body = got[-1][1]
    assert body.get("ok") is True
    assert body.get("release_id") == "ogs:demo:release:v1.4.0"


def test_integration_work_item_outcome_summary(seeded_workspace, monkeypatch) -> None:
    monkeypatch.setenv("LENSES_EXPERIMENTAL_OUTCOME_BRIDGE_B6", "1")
    _, conn = seeded_workspace
    from lenses.bridge.outcome_service import list_launches_for_work_item, outcome_summary_for_work_item

    assert "ogs:demo:b6:launch:auth-train" in list_launches_for_work_item(conn, "S-1842")
    s = outcome_summary_for_work_item(conn, "S-1842")
    assert s and s.get("outcome_launches")
    row = s["outcome_launches"][0]
    assert row.get("demand_signal_ids")


def test_post_launch_and_link_outcome(seeded_workspace, monkeypatch) -> None:
    monkeypatch.setenv("LENSES_EXPERIMENTAL_OUTCOME_BRIDGE_B6", "1")
    ws, _conn = seeded_workspace
    import urllib.parse

    from lenses.bridge.outcome_http import handle_outcome_b6_post

    got: list[tuple[int, dict]] = []

    def send_json(code: int, d: dict) -> None:
        got.append((code, d))

    def may_run(ip: str) -> bool:
        return True

    body_launch = {
        "id": "ogs:test:b6:launch:tmp",
        "display_name": "Tmp launch",
        "release_id": "ogs:demo:release:v1.4.0",
        "summary": "t",
    }
    assert handle_outcome_b6_post(
        workspace_root=ws,
        post_path="/api/launches",
        body=body_launch,
        send_json=send_json,
        client_ip="127.0.0.1",
        may_run_actions=may_run,
    )
    assert got[-1][0] == 201
    body_sig = {
        "kind": "adoption_signal",
        "id": "ogs:test:b6:sig:tmp",
        "display_name": "Tmp adoption",
        "summary": "s",
        "confidence": 0.5,
    }
    assert handle_outcome_b6_post(
        workspace_root=ws,
        post_path="/api/outcomes",
        body=body_sig,
        send_json=send_json,
        client_ip="127.0.0.1",
        may_run_actions=may_run,
    )
    assert got[-1][0] == 201
    assert handle_outcome_b6_post(
        workspace_root=ws,
        post_path="/api/launches/ogs:test:b6:launch:tmp/link-outcome",
        body={"outcome_entity_id": "ogs:test:b6:sig:tmp"},
        send_json=send_json,
        client_ip="127.0.0.1",
        may_run_actions=may_run,
    )
    assert got[-1][1].get("ok") is True
    from lenses.bridge.outcome_service import get_launch_bundle
    from lenses.orchestration_graph.db import connect as og_connect

    c2 = og_connect(ws)
    assert c2 is not None
    try:
        b = get_launch_bundle(c2, "ogs:test:b6:launch:tmp")
        assert any(str(s.get("id")) == "ogs:test:b6:sig:tmp" for s in (b.get("signals") or []))
    finally:
        c2.close()
