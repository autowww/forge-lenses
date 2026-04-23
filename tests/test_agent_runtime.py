"""Agent runtime dispatch, ledger, and sessions (DOCS-3)."""

from __future__ import annotations

from pathlib import Path

import pytest

from lenses.agent_runtime.dispatch import plan_dispatch, provider_ready
from lenses.agent_runtime.endpoint_registry import (
    CAPABILITY_WRITER_MEDIUM,
    build_endpoint_registry_payload,
    docs_health_slot_lookup_keys,
    normalize_slot_id,
)
from lenses.agent_runtime.ledger import append_model_call, read_ledger_tail, summarize_ledger
from lenses.agent_runtime import sessions as ars
from lenses.llm_settings_store import load_raw, merge_save


def test_normalize_slot_legacy_aliases() -> None:
    assert normalize_slot_id("local_writer") == CAPABILITY_WRITER_MEDIUM
    assert normalize_slot_id("writer.medium") == CAPABILITY_WRITER_MEDIUM


def test_build_endpoint_registry_payload_includes_capabilities_and_aliases(tmp_path: Path) -> None:
    payload = build_endpoint_registry_payload(tmp_path)
    assert isinstance(payload.get("capabilities"), list)
    assert payload.get("legacy_slot_aliases", {}).get("local_triage") == "triage.small"
    pol = payload.get("policy") or {}
    assert "capability_ids" in pol


def test_docs_health_slot_lookup_keys_include_legacy() -> None:
    keys = docs_health_slot_lookup_keys("writer.medium")
    assert "writer.medium" in keys
    assert "local_writer" in keys


def test_plan_dispatch_normalizes_legacy_local_writer(tmp_path: Path) -> None:
    merge_save(tmp_path, {"agent_runtime": {"allow_cloud_escalation": True, "allow_private_compat_url": True}})
    _chain, trace = plan_dispatch(tmp_path, "local_writer")
    assert trace.get("slot") == "writer.medium"
    assert trace.get("requested_slot") == "local_writer"
    assert trace.get("capability_id") == "writer.medium"


def test_plan_dispatch_prefers_ollama_for_capability_slot(tmp_path: Path) -> None:
    merge_save(tmp_path, {"agent_runtime": {"allow_cloud_escalation": True, "allow_private_compat_url": True}})
    chain, trace = plan_dispatch(tmp_path, "writer.medium")
    assert trace.get("slot") == "writer.medium"
    assert isinstance(chain, list)


def test_external_slot_skips_ollama(tmp_path: Path) -> None:
    merge_save(tmp_path, {"agent_runtime": {"allow_cloud_escalation": True, "allow_private_compat_url": False}})
    chain, trace = plan_dispatch(tmp_path, "external_writer")
    assert all(p != "ollama" for p in chain)
    assert trace.get("slot") == "external_writer"


def test_plan_dispatch_falls_back_when_ollama_unavailable(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    merge_save(
        tmp_path,
        {
            "agent_runtime": {"allow_cloud_escalation": True, "allow_private_compat_url": True},
            "openai_compatible_base_url": "http://127.0.0.1:19999/v1",
            "keys": {"openai_compatible": "sk-test"},
        },
    )

    def fake_ready(ws: Path, provider: str, raw: dict) -> tuple[bool, str]:
        if provider == "ollama":
            return False, "ollama_unreachable"
        if provider == "openai_compatible":
            return True, "ok"
        if provider == "openai":
            return True, "ok"
        return False, "skip"

    monkeypatch.setattr("lenses.agent_runtime.dispatch.provider_ready", fake_ready)
    chain, trace = plan_dispatch(tmp_path, "writer.medium")
    assert chain and chain[0] == "openai_compatible"
    assert trace.get("slot") == "writer.medium"
    reasons = [s.get("reason") for s in trace.get("steps_evaluated") or []]
    assert "local_unavailable" in reasons


def test_ledger_round_trip(tmp_path: Path) -> None:
    append_model_call(
        tmp_path,
        {
            "id": "t1",
            "ts": "2026-01-01T00:00:00+00:00",
            "endpoint_id": "ollama",
            "provider": "ollama",
            "adapter": "ollama",
            "model_slot": "writer.medium",
            "studio_task_id": "docs_health_writer",
            "model_id": "m",
            "input_tokens": 10,
            "output_tokens": 5,
            "total_tokens": 15,
            "token_counting_mode": "estimated",
            "elapsed_ms": 100,
            "ok": True,
            "session_id": "sess1",
            "project_slug": "p1",
            "scan_run_id": None,
            "cluster_id": None,
            "agent_definition_id": "docs_health_remediation",
            "dispatch_trace": None,
        },
    )
    rows = read_ledger_tail(tmp_path, max_lines=10)
    assert rows and rows[-1]["model_slot"] == "writer.medium"
    s = summarize_ledger(tmp_path, session_id="sess1")
    assert s["totals"]["calls"] == 1


def test_session_resume(tmp_path: Path) -> None:
    s = ars.create_session(tmp_path, kind="test", project_slug="demo")
    sid = str(s["id"])
    ars.append_event(tmp_path, sid, "ping", {"x": 1})
    s2 = ars.load_session(tmp_path, sid)
    assert s2 and len(s2.get("events") or []) >= 2
    evs = ars.list_events_since(tmp_path, sid, since_seq=-1)
    assert any(e.get("type") == "ping" for e in evs)


def test_provider_ready_unknown(tmp_path: Path) -> None:
    raw = load_raw(tmp_path)
    ok, detail = provider_ready(tmp_path, "not_a_provider", raw)
    assert ok is False
    assert detail
