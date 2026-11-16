"""Sprint B3: agentic bridge — discovery, drift, runs, approvals, APIs."""

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
    monkeypatch.setenv("LENSES_EXPERIMENTAL_AGENTIC_BRIDGE_B3", "1")
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
def empty_ws(tmp_path, monkeypatch):
    monkeypatch.setenv("LENSES_EXPERIMENTAL_ORCHESTRATION_GRAPH", "1")
    monkeypatch.setenv("LENSES_EXPERIMENTAL_AGENTIC_BRIDGE_B3", "1")
    monkeypatch.setenv("LENSES_ORCHESTRATION_AUTO_SEED", "0")
    ws = tmp_path / "workspace"
    ws.mkdir()
    (ws / ".lenses-local").mkdir(parents=True)
    forge = ws / "forge"
    forge.mkdir()
    (forge / "forge.config.yaml").write_text(
        "\n".join(
            [
                "versona:",
                "  families:",
                "    engineering: true",
                "  engineering_disciplines:",
                "    software_engineering: true",
                "",
            ]
        ),
        encoding="utf-8",
    )
    rules = ws / ".cursor" / "rules"
    rules.mkdir(parents=True)
    (rules / "versona-se.mdc").write_text("---\nname: se\n---\n", encoding="utf-8")
    agents = ws / "agents" / "recipes" / "demo"
    agents.mkdir(parents=True)
    (agents / "hello.md").write_text("# Demo recipe\n", encoding="utf-8")
    return ws


def test_forge_config_parse(empty_ws: Path) -> None:
    from lenses.bridge.agentic_discovery import discover_forge_config

    d = discover_forge_config(empty_ws)
    assert d.get("ok") is True
    assert "engineering" in (d.get("active_versona_families") or [])
    assert "software_engineering" in (d.get("active_disciplines") or [])


def test_recipe_file_discovery(empty_ws: Path) -> None:
    from lenses.bridge.agentic_bridge_registry import load_agentic_bridge_registry
    from lenses.bridge.agentic_discovery import discover_recipe_files

    reg = load_agentic_bridge_registry()
    files = discover_recipe_files(empty_ws, list(reg.get("recipe_scan_globs") or []))
    rels = [f["rel_path"] for f in files]
    assert any("agents/recipes/" in r for r in rels)


def test_drift_missing_rule_when_discipline_active(empty_ws: Path) -> None:
    from lenses.bridge.agentic_bridge_registry import load_agentic_bridge_registry
    from lenses.bridge.agentic_drift import compute_agentic_drift

    reg = load_agentic_bridge_registry()
    out = compute_agentic_drift(empty_ws, reg)
    assert out.get("ok") is True
    missing = out.get("missing_expected_rules") or []
    assert any(m.get("expected_file") == "versona-architecture.mdc" for m in missing)


def test_run_lifecycle_and_approval(empty_ws: Path, monkeypatch) -> None:
    monkeypatch.setenv("LENSES_EXPERIMENTAL_ORCHESTRATION_GRAPH", "1")
    monkeypatch.setenv("LENSES_EXPERIMENTAL_AGENTIC_BRIDGE_B3", "1")
    from lenses.orchestration_graph.db import connect
    from lenses.bridge.agentic_service import approve_agent_run, create_agent_run, get_entity_bundle

    conn = connect(empty_ws)
    assert conn is not None
    r1 = create_agent_run(
        conn,
        {"title": "RO", "execution_mode": "read_only", "owner": "t"},
    )
    assert r1.get("ok") is True
    assert not r1.get("approval_request_id")
    r2 = create_agent_run(
        conn,
        {"title": "Gated", "execution_mode": "approval_gated", "owner": "t"},
    )
    assert r2.get("ok") is True
    assert r2.get("approval_request_id")
    bad = approve_agent_run(conn, r2["id"], {"approved_by": "x"})
    assert bad.get("ok") is False
    good = approve_agent_run(
        conn,
        r2["id"],
        {"approved_by": "x", "confirm_human_approval": True},
    )
    assert good.get("ok") is True
    bundle = get_entity_bundle(conn, r2["id"])
    assert bundle.get("ok") is True
    conn.close()


def test_http_contracts(empty_ws: Path, monkeypatch) -> None:
    monkeypatch.setenv("LENSES_EXPERIMENTAL_ORCHESTRATION_GRAPH", "1")
    monkeypatch.setenv("LENSES_EXPERIMENTAL_AGENTIC_BRIDGE_B3", "1")
    from lenses.bridge.agentic_http import handle_agentic_b3_get, handle_agentic_b3_post

    cap: list[tuple[int, dict]] = []

    def send_json(s: int, d: dict) -> None:
        cap.append((s, d))

    assert handle_agentic_b3_get(
        workspace_root=empty_ws,
        path="/api/agents/drift",
        parsed=urllib.parse.urlparse("/api/agents/drift"),
        send_json=send_json,
    )
    assert cap[-1][0] == 200
    assert cap[-1][1].get("missing_expected_rules") is not None

    cap.clear()
    assert handle_agentic_b3_post(
        workspace_root=empty_ws,
        post_path="/api/agents/runs",
        body={"title": "API run", "execution_mode": "read_only"},
        send_json=send_json,
        client_ip="127.0.0.1",
        may_run_actions=lambda _ip: True,
    )
    assert cap[-1][0] == 201


def test_link_output_to_methodology_artifact_integrity(graph_conn) -> None:
    from lenses.bridge.agentic_service import link_agent_output_to_artifact

    r = link_agent_output_to_artifact(
        graph_conn,
        "ogs:demo:b3:out:summary",
        "ogs:demo:b2:impl-ev",
    )
    assert r.get("ok") is False

    from lenses.bridge.methodology_service import upsert_ogs_entity

    upsert_ogs_entity(
        graph_conn,
        entity_id="ogs:test:b3:art:1",
        kind="methodology_artifact",
        display_name="Extra artifact",
        summary="for link test",
        payload={"forge_profile": "implementation_evidence", "status": "test"},
    )
    graph_conn.commit()
    r2 = link_agent_output_to_artifact(
        graph_conn,
        "ogs:demo:b3:out:summary",
        "ogs:test:b3:art:1",
    )
    assert r2.get("ok") is True
