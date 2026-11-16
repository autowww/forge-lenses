"""Orchestration graph: migrations, seed, trace query."""

from __future__ import annotations

import json
import os
import sqlite3
from pathlib import Path

import pytest

from lenses.orchestration_graph.feature_flag import (
    experimental_orchestration_graph_enabled,
    orchestration_auto_seed_enabled,
)
from lenses.orchestration_graph.migrate import apply_migrations, current_schema_version
from lenses.orchestration_graph.query import fetch_entity, trace_subgraph
from lenses.orchestration_graph.seed_demo import apply_demo_bundle, entity_count
from lenses.orchestration_graph.db import orchestration_db_path


def _conn(tmp_path: Path) -> sqlite3.Connection:
    local = tmp_path / ".lenses-local"
    local.mkdir(parents=True)
    db = local / "test-ogs.sqlite"
    conn = sqlite3.connect(str(db))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    apply_migrations(conn)
    return conn


def _demo_bundle() -> dict:
    p = Path(__file__).resolve().parent.parent / "lenses" / "fixtures" / "orchestration-graph.demo.json"
    return json.loads(p.read_text(encoding="utf-8"))


def test_migration_sets_schema_version(tmp_path: Path) -> None:
    conn = _conn(tmp_path)
    assert current_schema_version(conn) == 8
    conn.close()


def test_seed_and_trace_story_e2e(tmp_path: Path) -> None:
    conn = _conn(tmp_path)
    assert entity_count(conn) == 0
    apply_demo_bundle(conn, _demo_bundle())
    assert entity_count(conn) == 121

    story_id = "ogs:demo:story:rate-limit-auth"
    root = fetch_entity(conn, story_id)
    assert root is not None
    assert root["kind"] == "story"

    out = trace_subgraph(conn, story_id, max_depth=10, max_nodes=500)
    assert out["ok"] is True
    assert len(out["nodes"]) == 114
    assert len(out["edges"]) == 158
    kinds = {n["kind"] for n in out["nodes"]}
    for k in (
        "objective",
        "initiative",
        "epic",
        "story",
        "task",
        "repo",
        "branch",
        "change_request",
        "commit",
        "build",
        "artifact",
        "release",
        "environment",
        "test_run",
        "test_plan",
        "test_suite",
        "test_case",
        "defect",
        "security_finding",
        "compliance_exception",
        "control",
        "vulnerability",
        "incident",
        "service",
        "postmortem",
        "evidence",
        "workstream",
        "demand_signal",
        "scoped_commitment",
        "contributor",
        "gate",
        "methodology_artifact",
        "decision_record",
        "review_pack",
        "assay_packet",
        "versona_family",
        "versona_profile",
        "tasklet",
        "recipe",
        "launch_pack",
        "agent_run",
        "agent_step",
        "agent_output",
        "approval_request",
        "policy_rule",
        "execution_target",
        "drift_report",
        "rules_manifest",
        "prompt_template",
        "ceremony_intent",
        "ceremony_template",
        "ceremony_mapping",
        "ceremony_instance",
        "delivery_mode",
        "ceremony_output",
        "participant_role",
        "moderator_role",
        "signoff_record",
        "followup_action",
        "required_artifact_ref",
        "decision_binding_rule",
        "handoff_package",
        "handoff_target",
        "prompt_bundle",
        "context_bundle",
        "execution_session",
        "execution_return",
        "sync_checkpoint",
        "output_manifest",
        "file_change_summary",
        "code_review_ref",
        "build_test_return",
        "launch_record",
        "outcome_signal",
        "metric_snapshot",
        "experiment_result",
        "customer_feedback_ref",
        "support_signal",
        "adoption_signal",
        "retention_signal",
        "satisfaction_signal",
        "revenue_proxy_signal",
        "learning_summary",
        "followon_ore_candidate",
    ):
        assert k in kinds

    # Typed edges present
    kinds_e = {(e["from_id"], e["to_id"], e["kind"]) for e in out["edges"]}
    assert ("ogs:demo:cr:184", "ogs:demo:story:rate-limit-auth", "implements") in kinds_e
    assert ("ogs:demo:release:v1.4.0", "ogs:demo:env:production", "deploys") in kinds_e
    assert ("ogs:demo:story:rate-limit-auth", "ogs:demo:evidence:wbs-auth", "documented_by") in kinds_e
    assert ("ogs:demo:testcase:rate-001", "ogs:demo:story:rate-limit-auth", "validates") in kinds_e
    assert ("ogs:demo:testcase:rate-001", "ogs:demo:defect:441", "raised_defect") in kinds_e
    assert ("ogs:demo:defect:441", "ogs:demo:release:v1.4.0", "affects") in kinds_e
    assert ("ogs:demo:sf:secret-leak", "ogs:demo:story:rate-limit-auth", "affects") in kinds_e
    assert ("ogs:demo:exception:exc-demo", "ogs:demo:sf:secret-leak", "accepted_risk_for") in kinds_e
    assert ("ogs:demo:control:soc2-cc6", "ogs:demo:release:v1.4.0", "satisfies") in kinds_e
    assert ("ogs:demo:incident:prod-auth-latency", "ogs:demo:story:rate-limit-auth", "affects") in kinds_e
    assert ("ogs:demo:incident:prod-auth-latency", "ogs:demo:release:v1.4.0", "triggered_after") in kinds_e
    assert ("ogs:demo:incident:prod-auth-latency", "ogs:demo:svc:forge-web", "impacts") in kinds_e
    assert ("ogs:demo:pm:auth-latency-2026", "ogs:demo:incident:prod-auth-latency", "analyzes") in kinds_e
    assert ("ogs:demo:demand:ore-auth-throttle", "ogs:demo:scoped:ingot-auth-q2", "decomposes_to") in kinds_e
    assert ("ogs:demo:release:v1.4.0", "ogs:demo:gate:assay-auth-release", "gated_by") in kinds_e
    assert ("ogs:demo:b2:psp", "ogs:demo:story:rate-limit-auth", "decomposes_to") in kinds_e
    assert ("ogs:demo:b2:adr-auth", "ogs:demo:story:rate-limit-auth", "references") in kinds_e
    assert ("ogs:demo:b2:rp-auth", "ogs:demo:story:rate-limit-auth", "aggregates") in kinds_e
    assert ("ogs:demo:b3:run:readonly", "ogs:demo:story:rate-limit-auth", "references") in kinds_e
    assert ("ogs:demo:b3:run:readonly", "ogs:demo:b3:out:summary", "emits") in kinds_e
    assert ("ogs:demo:b3:out:summary", "ogs:demo:b2:impl-ev", "references") in kinds_e
    assert ("ogs:demo:b3:run:gated", "ogs:demo:b3:apr:pending", "seeks_approval") in kinds_e
    assert ("ogs:demo:b4:inst:hybrid", "ogs:demo:b4:tpl:charge", "instantiates") in kinds_e
    assert ("ogs:demo:b4:so:alex", "ogs:demo:b4:inst:binding", "approves") in kinds_e
    assert ("ogs:demo:b4:out:next", "ogs:demo:b2:directive-sec", "references") in kinds_e
    assert ("ogs:demo:b5:pkg:auth-rate", "ogs:demo:story:rate-limit-auth", "scopes_handoff") in kinds_e
    assert ("ogs:demo:b5:sess:auth", "ogs:demo:b5:pkg:auth-rate", "session_for") in kinds_e
    assert ("ogs:demo:b5:ret:auth", "ogs:demo:b5:sess:auth", "derived_from") in kinds_e
    assert ("ogs:demo:b6:launch:auth-train", "ogs:demo:release:v1.4.0", "launch_for") in kinds_e
    assert ("ogs:demo:b6:sig:adopt", "ogs:demo:b6:launch:auth-train", "outcome_observed") in kinds_e
    assert ("ogs:demo:b6:learn:postv14", "ogs:demo:b6:ore:burst", "proposes_followon") in kinds_e
    assert ("ogs:demo:b6:ore:burst", "ogs:demo:b6:demand:burst", "bridges_to_demand") in kinds_e
    conn.close()


def test_trace_missing_entity(tmp_path: Path) -> None:
    conn = _conn(tmp_path)
    out = trace_subgraph(conn, "ogs:missing:x", max_depth=2, max_nodes=50)
    assert out["ok"] is False
    assert out["error"] == "entity_not_found"
    conn.close()


def test_feature_flags_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("LENSES_EXPERIMENTAL_ORCHESTRATION_GRAPH", raising=False)
    assert experimental_orchestration_graph_enabled() is True
    monkeypatch.setenv("LENSES_EXPERIMENTAL_ORCHESTRATION_GRAPH", "0")
    assert experimental_orchestration_graph_enabled() is False

    monkeypatch.delenv("LENSES_ORCHESTRATION_AUTO_SEED", raising=False)
    assert orchestration_auto_seed_enabled() is True
    monkeypatch.setenv("LENSES_ORCHESTRATION_AUTO_SEED", "0")
    assert orchestration_auto_seed_enabled() is False


def test_orchestration_db_path_under_lenses_local(tmp_path: Path) -> None:
    p = orchestration_db_path(tmp_path)
    assert p.name == "lenses-orchestration.sqlite"
    assert p.parent.name == ".lenses-local"
