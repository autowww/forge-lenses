"""Sprint B4: ceremony bridge — mappings, delivery modes, sign-off, outputs, APIs."""

from __future__ import annotations

import json
import urllib.parse
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
FIXTURE = ROOT / "lenses" / "fixtures" / "orchestration-graph.demo.json"


@pytest.fixture
def seeded_workspace(tmp_path, monkeypatch):
    monkeypatch.setenv("LENSES_EXPERIMENTAL_ORCHESTRATION_GRAPH", "1")
    monkeypatch.setenv("LENSES_EXPERIMENTAL_CEREMONY_BRIDGE_B4", "1")
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


def test_mapping_validation_rejects_mislabeled_forge_ritual() -> None:
    from lenses.bridge.ceremony_service import validate_projection_label

    bad = validate_projection_label(
        methodology="forge",
        intent_id="C2",
        label="Stand-up",
        mapping_id="map-c2-charge",
    )
    assert bad.get("ok") is False
    assert bad.get("error") == "forge_label_not_mapped"

    good = validate_projection_label(
        methodology="forge",
        intent_id="C2",
        label="Charge",
        mapping_id="map-c2-charge",
    )
    assert good.get("ok") is True


def test_delivery_mode_blocks_binding_without_signoff(seeded_workspace, monkeypatch) -> None:
    monkeypatch.setenv("LENSES_EXPERIMENTAL_CEREMONY_BRIDGE_B4", "1")
    _, conn = seeded_workspace
    from lenses.bridge.ceremony_service import add_ceremony_output

    r = add_ceremony_output(
        conn,
        "ogs:demo:b4:inst:hybrid",
        {"output_type": "directive", "summary": "should fail"},
    )
    assert r.get("ok") is False
    assert r.get("error") == "binding_requires_human_signoff"


def test_readiness_hybrid_vs_binding(seeded_workspace, monkeypatch) -> None:
    monkeypatch.setenv("LENSES_EXPERIMENTAL_CEREMONY_BRIDGE_B4", "1")
    _, conn = seeded_workspace
    from lenses.bridge.ceremony_service import readiness_payload

    h = readiness_payload(conn, "ogs:demo:b4:inst:hybrid")
    assert h.get("ok") is True
    assert "approved_next_steps" in (h.get("missing_required_outputs") or [])
    assert h.get("missing_signoffs")

    b = readiness_payload(conn, "ogs:demo:b4:inst:binding")
    assert b.get("ok") is True
    assert b.get("complete") is True


def test_template_instantiation_and_non_binding_mode(seeded_workspace, monkeypatch) -> None:
    monkeypatch.setenv("LENSES_EXPERIMENTAL_CEREMONY_BRIDGE_B4", "1")
    _, conn = seeded_workspace
    from lenses.bridge.ceremony_service import add_ceremony_output, create_ceremony_instance

    body = {
        "template_id": "ogs:demo:b4:tpl:readiness",
        "delivery_mode": "versona_only_non_binding",
        "inputs": {
            "work_unit_ids": ["ogs:demo:story:rate-limit-auth"],
            "artifact_ids": ["ogs:demo:b2:rp-auth"],
            "evidence_ids": ["ogs:demo:evidence:wbs-auth"],
            "metrics_snapshot": {"ok": True},
            "risks_issues": ["none"],
        },
    }
    r = create_ceremony_instance(conn, body)
    assert r.get("ok") is True
    iid = str(r.get("id") or "")
    assert iid.startswith("ogs:")

    bad = add_ceremony_output(conn, iid, {"output_type": "directive", "summary": "x"})
    assert bad.get("ok") is False
    assert bad.get("error") == "binding_output_not_allowed_for_delivery_mode"

    good = add_ceremony_output(conn, iid, {"output_type": "meeting_summary", "summary": "synth"})
    assert good.get("ok") is True


def test_signoff_then_binding_output(seeded_workspace, monkeypatch) -> None:
    monkeypatch.setenv("LENSES_EXPERIMENTAL_CEREMONY_BRIDGE_B4", "1")
    _, conn = seeded_workspace
    from lenses.bridge.ceremony_service import add_ceremony_output, create_ceremony_instance, signoff_ceremony

    r = create_ceremony_instance(
        conn,
        {
            "template_id": "ogs:demo:b4:tpl:charge",
            "delivery_mode": "human_only",
            "inputs": {
                "work_unit_ids": ["ogs:demo:story:rate-limit-auth"],
                "artifact_ids": ["ogs:demo:b2:psp"],
                "evidence_ids": ["ogs:demo:evidence:wbs-auth"],
                "metrics_snapshot": {},
                "risks_issues": ["r1"],
            },
        },
    )
    assert r.get("ok") is True
    iid = str(r["id"])

    denied = add_ceremony_output(conn, iid, {"output_type": "approved_next_steps", "summary": "scope"})
    assert denied.get("error") == "binding_requires_human_signoff"

    so = signoff_ceremony(
        conn,
        iid,
        {"signed_by": "qa-tester", "signer_role": "charge_owner", "confirm_human_signoff": True},
    )
    assert so.get("ok") is True

    ok = add_ceremony_output(
        conn,
        iid,
        {
            "output_type": "approved_next_steps",
            "summary": "Committed scope items recorded.",
            "linked_decision_id": "ogs:demo:b2:adr-auth",
        },
    )
    assert ok.get("ok") is True


def test_http_get_contract(seeded_workspace, monkeypatch) -> None:
    monkeypatch.setenv("LENSES_EXPERIMENTAL_CEREMONY_BRIDGE_B4", "1")
    ws, _ = seeded_workspace
    from lenses.bridge.ceremony_http import handle_ceremony_b4_get

    captured: list[tuple[int, dict]] = []

    def send_json(code: int, d: dict) -> None:
        captured.append((code, d))

    ok = handle_ceremony_b4_get(
        workspace_root=ws,
        path="/api/ceremonies/intents",
        parsed=urllib.parse.urlparse("/api/ceremonies/intents"),
        send_json=send_json,
    )
    assert ok is True
    assert captured[-1][0] == 200
    body = captured[-1][1]
    assert body.get("ok") is True
    assert "C2" in (body.get("intents") or {})
