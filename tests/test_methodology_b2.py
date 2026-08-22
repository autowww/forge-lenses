"""Sprint B2: methodology artifacts, decisions, packs, ingest, readiness, HTTP handlers."""

from __future__ import annotations

import json
import urllib.parse
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
FIXTURE = ROOT / "lenses" / "fixtures" / "orchestration-graph.demo.json"


@pytest.fixture
def graph_conn(tmp_path, monkeypatch):
    monkeypatch.setenv("LENSES_EXPERIMENTAL_ORCHESTRATION_GRAPH", "1")
    monkeypatch.setenv("LENSES_EXPERIMENTAL_METHODOLOGY_BRIDGE_B2", "1")
    monkeypatch.setenv("LENSES_ORCHESTRATION_AUTO_SEED", "0")
    ws = tmp_path / "workspace"
    ws.mkdir()
    (ws / ".lenses-local").mkdir(parents=True)
    from lenses.orchestration_graph.db import connect
    from lenses.orchestration_graph.seed_demo import apply_demo_bundle

    conn = connect(ws)
    assert conn is not None
    bundle = json.loads(FIXTURE.read_text(encoding="utf-8"))
    apply_demo_bundle(conn, bundle)
    yield conn
    conn.close()


@pytest.fixture
def empty_ws_conn(tmp_path, monkeypatch):
    monkeypatch.setenv("LENSES_EXPERIMENTAL_ORCHESTRATION_GRAPH", "1")
    monkeypatch.setenv("LENSES_EXPERIMENTAL_METHODOLOGY_BRIDGE_B2", "1")
    monkeypatch.setenv("LENSES_ORCHESTRATION_AUTO_SEED", "0")
    ws = tmp_path / "workspace"
    ws.mkdir()
    (ws / ".lenses-local").mkdir(parents=True)
    from lenses.orchestration_graph.db import connect
    from lenses.orchestration_graph.migrate import apply_migrations

    conn = connect(ws)
    assert conn is not None
    apply_migrations(conn)
    yield conn, ws
    conn.close()


def test_forge_profile_maps_to_neutral_category() -> None:
    from lenses.bridge.methodology_b2_registry import load_methodology_b2_registry

    reg = load_methodology_b2_registry()
    profiles = reg.get("forge_artifact_profiles") or {}
    assert profiles["ore"]["neutral_category"] == "demand_signal"
    assert profiles["product_spark_plan"]["neutral_category"] == "planning_artifact"
    assert profiles["implementation_evidence"]["neutral_category"] == "evidence"
    dprof = reg.get("decision_type_profiles") or {}
    assert "gates" in dprof["adr"]
    assert dprof["directive"]["human_signoff_required_for_binding"] is True


def test_markdown_ingest_creates_methodology_row(empty_ws_conn) -> None:
    conn, ws = empty_ws_conn
    md_dir = ws / "docs" / "demo"
    md_dir.mkdir(parents=True)
    p = md_dir / "impl-note.md"
    p.write_text(
        "---\ntitle: Demo implementation note\nlenses_forge_profile: implementation_evidence\n---\n\nBody.\n",
        encoding="utf-8",
    )
    from lenses.bridge.methodology_service import import_markdown_paths

    out = import_markdown_paths(ws, conn, rel_paths=["docs/demo/impl-note.md"])
    assert out.get("ok") is True
    assert out.get("count") == 1
    row = conn.execute(
        "SELECT id FROM ogs_entity WHERE kind = 'methodology_artifact' LIMIT 1"
    ).fetchone()
    assert row is not None
    idx = conn.execute(
        "SELECT rel_path FROM bridge_evidence_doc_index WHERE rel_path = ?",
        ("docs/demo/impl-note.md",),
    ).fetchone()
    assert idx is not None


def test_decision_lifecycle_binding_signoff_requires_confirm(empty_ws_conn) -> None:
    conn, _ws = empty_ws_conn
    from lenses.bridge.methodology_service import create_decision, signoff_decision

    r = create_decision(
        conn,
        {
            "decision_type": "adr",
            "title": "Test ADR",
            "binding": True,
            "decision_summary": "Pick A",
        },
    )
    assert r.get("ok") is True
    eid = r["id"]
    bad = signoff_decision(conn, eid, {"signed_by": "t"})
    assert bad.get("ok") is False
    assert bad.get("error") == "human_signoff_required"
    good = signoff_decision(
        conn,
        eid,
        {"signed_by": "t", "confirm_human_signoff": True},
    )
    assert good.get("ok") is True
    assert good["payload"].get("signoff_state") == "signed"


def test_review_pack_and_assay_aggregation(graph_conn) -> None:
    from lenses.bridge.methodology_service import build_assay_packet_view, build_review_pack_view

    rp = build_review_pack_view(graph_conn, "ogs:demo:b2:rp-auth")
    assert rp.get("ok") is True
    wu = rp["sections"]["work_units"]
    assert "ogs:demo:story:rate-limit-auth" in wu
    assert "ogs:demo:cr:184" in rp["sections"]["linked_code"]
    assert "ogs:demo:b2:impl-ev" in rp["sections"]["evidence_attachments"]
    assert "ogs:demo:b2:adr-auth" in rp["sections"]["outstanding_decisions"]

    ap = build_assay_packet_view(graph_conn, "ogs:demo:b2:ap-auth")
    assert ap.get("ok") is True
    assert "ogs:demo:release:v1.4.0" in ap["sections"]["release_candidates"]
    assert "ogs:demo:build:ci-9912" in ap["sections"]["evidence_links"]
    assert "ogs:demo:exception:exc-demo" in ap["sections"]["exception_records"]
    gaps = ap.get("readiness_gaps") or []
    assert gaps == []


def test_readiness_gaps_when_missing_assay(empty_ws_conn) -> None:
    conn, _ws = empty_ws_conn
    from lenses.bridge.methodology_service import create_decision, signoff_decision, readiness_gaps_for_release
    from lenses.bridge.methodology_service import upsert_ogs_entity
    from lenses.orchestration_graph.query import fetch_entity

    upsert_ogs_entity(
        conn,
        entity_id="ogs:test:rel:a",
        kind="release",
        display_name="R1",
        summary="s",
        payload={"tag": "v0"},
    )
    conn.commit()
    assert fetch_entity(conn, "ogs:test:rel:a") is not None

    create_decision(
        conn,
        {
            "id": "ogs:test:dir:1",
            "decision_type": "directive",
            "title": "D",
            "binding": True,
            "decision_summary": "x",
        },
    )
    signoff_decision(
        conn,
        "ogs:test:dir:1",
        {"signed_by": "u", "confirm_human_signoff": True},
    )
    out = readiness_gaps_for_release(conn, "ogs:test:rel:a")
    assert out.get("ok") is True
    kinds = {g.get("kind") for g in (out.get("gaps") or [])}
    assert "missing_required_artifact" in kinds


def test_http_get_readiness_and_records(tmp_path, monkeypatch):
    monkeypatch.setenv("LENSES_EXPERIMENTAL_ORCHESTRATION_GRAPH", "1")
    monkeypatch.setenv("LENSES_EXPERIMENTAL_METHODOLOGY_BRIDGE_B2", "1")
    ws = tmp_path / "w"
    ws.mkdir()
    (ws / ".lenses-local").mkdir()
    from lenses.orchestration_graph.db import connect
    from lenses.orchestration_graph.seed_demo import apply_demo_bundle

    conn = connect(ws)
    assert conn is not None
    apply_demo_bundle(conn, json.loads(FIXTURE.read_text(encoding="utf-8")))
    conn.close()

    from lenses.bridge.methodology_http import handle_methodology_b2_get

    captured: list[tuple[int, dict]] = []

    def send_json(status: int, d: dict) -> None:
        captured.append((status, d))

    u = urllib.parse.urlparse(
        "/api/methodology/readiness?release_id=" + urllib.parse.quote("ogs:demo:release:v1.4.0", safe="")
    )
    assert handle_methodology_b2_get(
        workspace_root=ws,
        path="/api/methodology/readiness",
        parsed=u,
        send_json=send_json,
    )
    assert captured[-1][0] == 200
    assert captured[-1][1].get("gaps") == []

    captured.clear()
    u2 = urllib.parse.urlparse("/api/methodology/records/ogs:demo:b2:psp")
    assert handle_methodology_b2_get(
        workspace_root=ws,
        path="/api/methodology/records/ogs:demo:b2:psp",
        parsed=u2,
        send_json=send_json,
    )
    assert captured[-1][0] == 200
    assert captured[-1][1].get("entity", {}).get("id") == "ogs:demo:b2:psp"


def test_evidence_search_empty_query_lists_recent(graph_conn) -> None:
    from lenses.bridge.methodology_service import evidence_search

    out = evidence_search(graph_conn, "", limit=20)
    assert out.get("ok") is True
    assert len(out.get("hits") or []) >= 1


def test_http_post_decision_validation(tmp_path, monkeypatch):
    monkeypatch.setenv("LENSES_EXPERIMENTAL_ORCHESTRATION_GRAPH", "1")
    monkeypatch.setenv("LENSES_EXPERIMENTAL_METHODOLOGY_BRIDGE_B2", "1")
    ws = tmp_path / "w2"
    ws.mkdir()
    (ws / ".lenses-local").mkdir()
    from lenses.bridge.methodology_http import handle_methodology_b2_post

    got: list[tuple[int, dict]] = []

    def send_json(status: int, d: dict) -> None:
        got.append((status, d))

    assert handle_methodology_b2_post(
        workspace_root=ws,
        post_path="/api/decisions",
        body={"decision_type": "not_a_real_type", "title": "x"},
        send_json=send_json,
        client_ip="127.0.0.1",
        may_run_actions=lambda _ip: True,
    )
    assert got[-1][0] == 400
    assert got[-1][1].get("error") == "invalid_decision_type"


def test_demo_lineage_in_bridge_trace(graph_conn) -> None:
    from lenses.bridge.registry import load_bridge_registry
    from lenses.bridge.trace_service import bridge_trace_payload

    reg = load_bridge_registry()
    out = bridge_trace_payload(
        graph_conn,
        "ogs:demo:demand:ore-auth-throttle",
        reg,
        max_depth=14,
        max_nodes=400,
    )
    assert out.get("ok") is True
    ids = {n.get("id") for n in (out.get("nodes") or [])}
    assert "ogs:demo:b2:psp" in ids
    assert "ogs:demo:b2:adr-auth" in ids
