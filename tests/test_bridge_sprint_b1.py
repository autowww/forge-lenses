"""Sprint B1: bridge registry, projections, trace API payloads, and demo chain."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
FIXTURE = ROOT / "lenses" / "fixtures" / "orchestration-graph.demo.json"


@pytest.fixture
def graph_conn(tmp_path, monkeypatch):
    monkeypatch.setenv("LENSES_EXPERIMENTAL_ORCHESTRATION_GRAPH", "1")
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


def test_registry_version_and_validation():
    from lenses.bridge.registry import load_bridge_registry, validate_registry_struct

    reg = load_bridge_registry()
    assert reg.schema_version
    assert reg.registry_version
    assert validate_registry_struct(reg) == []


def test_term_lookup_and_collisions():
    from lenses.bridge.registry import load_bridge_registry

    reg = load_bridge_registry()
    row = reg.lookup_neutral_term("work_unit")
    assert row is not None
    assert "Forge Spark" in str(row.get("forge_labels"))
    cols = reg.term_collisions()
    assert any(c.get("id") == "forge_spark_vs_product_spark_plan" for c in cols)


def test_projection_lenses(graph_conn):
    from lenses.bridge.projection import project_entity
    from lenses.bridge.registry import load_bridge_registry
    from lenses.orchestration_graph.query import fetch_entity

    reg = load_bridge_registry()
    ent = fetch_entity(graph_conn, "ogs:demo:story:rate-limit-auth")
    assert ent is not None
    forge = project_entity(ent, reg, "forge")
    assert forge["canonical_kind"] == "work_unit"
    assert isinstance(forge.get("labels"), list)
    neutral = project_entity(ent, reg, "neutral")
    assert neutral["canonical_kind"] == "work_unit"


def test_traceability_score_and_gaps(graph_conn):
    from lenses.bridge.registry import load_bridge_registry
    from lenses.bridge.trace_service import compute_gaps, compute_traceability_score

    reg = load_bridge_registry()
    sid = "ogs:demo:story:rate-limit-auth"
    score = compute_traceability_score(graph_conn, sid, reg)
    assert score.get("ok") is True
    assert 0.0 <= float(score.get("score", 0)) <= 1.0
    gaps = compute_gaps(graph_conn, sid, reg)
    assert gaps.get("ok") is True
    assert isinstance(gaps.get("gaps"), list)


def test_bridge_trace_payload_enriches_nodes(graph_conn):
    from lenses.bridge.registry import load_bridge_registry
    from lenses.bridge.trace_service import bridge_trace_payload

    reg = load_bridge_registry()
    out = bridge_trace_payload(graph_conn, "ogs:demo:demand:ore-auth-throttle", reg, max_depth=6, max_nodes=200)
    assert out.get("ok") is True
    nodes = out.get("nodes") or []
    assert nodes
    sample = next((n for n in nodes if n.get("id") == "ogs:demo:story:rate-limit-auth"), None)
    assert sample is not None
    assert sample.get("canonical_kind") == "work_unit"
    assert "projections" in sample
    assert "spine_meta" in sample
    assert "created_at" in sample["spine_meta"]
    bridge = out.get("bridge") or {}
    assert "traceability_score" in bridge


def test_downstream_chain_demand_to_release(graph_conn):
    from lenses.bridge.registry import load_bridge_registry
    from lenses.bridge.trace_service import bridge_trace_payload

    reg = load_bridge_registry()
    out = bridge_trace_payload(graph_conn, "ogs:demo:demand:ore-auth-throttle", reg, max_depth=12, max_nodes=300)
    assert out.get("ok") is True
    ids = {n.get("id") for n in (out.get("nodes") or [])}
    assert "ogs:demo:scoped:ingot-auth-q2" in ids
    assert "ogs:demo:story:rate-limit-auth" in ids
    assert "ogs:demo:release:v1.4.0" in ids
    assert "ogs:demo:gate:assay-auth-release" in ids


def test_immediate_neighbors(graph_conn):
    from lenses.bridge.registry import load_bridge_registry
    from lenses.bridge.trace_service import immediate_neighbors

    reg = load_bridge_registry()
    out = immediate_neighbors(graph_conn, "ogs:demo:story:rate-limit-auth", reg)
    assert out.get("ok") is True
    assert out.get("outgoing_edges") and out.get("incoming_edges")
    assert isinstance(out.get("neighbor_entities"), list)


def test_insert_bridge_link(graph_conn):
    from lenses.bridge.trace_service import insert_bridge_link
    from lenses.orchestration_graph.query import fetch_entity

    out = insert_bridge_link(
        graph_conn,
        from_id="ogs:demo:task:token-bucket",
        to_id="ogs:demo:contrib:lead-alex",
        kind="reviewed_by",
    )
    assert out.get("ok") is True
    assert fetch_entity(graph_conn, "ogs:demo:contrib:lead-alex") is not None