"""Headless Copilot question-bank E2E (engine only — no Studio UI)."""

from __future__ import annotations

import json
import os
import threading
from http.client import HTTPConnection
from pathlib import Path

import pytest

from lenses import llm_chat

from tests.copilot_eval_harness import (
    evaluate_orchestration,
    evaluate_quality_heuristic,
    evaluate_quality_llm_judge,
    live_env_enabled,
    live_judge_enabled,
    live_model_override,
    live_provider,
    load_question_bank,
    make_grounding_aware_mock_chat,
    resolve_workspace_for_run,
    run_copilot_case,
    scan_state_for_workspace,
)

pytest.importorskip("yaml")


@pytest.fixture
def question_bank_workspace(tmp_path: Path) -> Path:
    return resolve_workspace_for_run(tmp_path)


@pytest.fixture
def question_bank_scan(question_bank_workspace: Path) -> dict:
    return scan_state_for_workspace(question_bank_workspace)


@pytest.mark.parametrize("case", load_question_bank(), ids=lambda c: c.id)
def test_copilot_question_bank_orchestration_mock(
    monkeypatch: pytest.MonkeyPatch,
    question_bank_workspace: Path,
    question_bank_scan: dict,
    case,
) -> None:
    """Mock LLM — validates strategy, grounding, citations, map-reduce plan (CI-safe)."""
    monkeypatch.delenv("LENSES_EXPERIMENTAL_SDLC_COPILOT", raising=False)
    monkeypatch.setenv("LENSES_COPILOT_MAP_REDUCE", "1")
    monkeypatch.setattr(llm_chat, "chat", make_grounding_aware_mock_chat())

    events: list[tuple[str, dict]] = []

    def on_event(typ: str, payload: dict) -> None:
        events.append((typ, payload))

    result = run_copilot_case(
        case,
        workspace_root=question_bank_workspace,
        scan_state=question_bank_scan,
        provider="ollama",
        on_event=on_event,
    )
    verdict = evaluate_orchestration(case, result)
    assert verdict.passed, verdict.summary()


@pytest.mark.parametrize("case", load_question_bank(), ids=lambda c: c.id)
@pytest.mark.skipif(
    not live_env_enabled(),
    reason="Set LENSES_COPILOT_LIVE=1 to run live Copilot question-bank E2E",
)
def test_copilot_question_bank_live(
    question_bank_workspace: Path,
    question_bank_scan: dict,
    case,
) -> None:
    """Live LLM — full engine path + heuristic and optional LLM judge."""
    provider = live_provider()
    model = live_model_override()
    result = run_copilot_case(
        case,
        workspace_root=question_bank_workspace,
        scan_state=question_bank_scan,
        provider=provider,
        model_override=model,
    )
    assert result.get("ok") is True, f"copilot failed: {result.get('error')} {result.get('detail')}"

    orch = evaluate_orchestration(case, result)
    assert orch.passed, orch.summary()

    quality = evaluate_quality_heuristic(case, result)
    assert quality.passed, quality.summary()

    if live_judge_enabled() and _quality_expect_rubric(case):
        judge = evaluate_quality_llm_judge(
            case,
            result,
            provider=provider,
            workspace_root=question_bank_workspace,
            model_override=model,
        )
        assert judge.passed, judge.summary()


def _quality_expect_rubric(case) -> bool:
    exp = case.expect.get("quality") if isinstance(case.expect, dict) else {}
    return bool(isinstance(exp, dict) and str(exp.get("rubric") or "").strip())


@pytest.fixture
def copilot_http_server(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Loopback HTTP server for sync ``POST /api/sdlc-copilot/chat`` (no SSE)."""
    from http.server import ThreadingHTTPServer

    from lenses.auth_session import SessionManager
    from lenses.serve import LensesHandler

    wr = resolve_workspace_for_run(tmp_path / "http-ws")
    monkeypatch.setenv("LENSES_ALLOW_ACTIONS", "1")
    monkeypatch.setenv("LENSES_COPILOT_MAP_REDUCE", "1")
    monkeypatch.setattr(llm_chat, "chat", make_grounding_aware_mock_chat())

    LensesHandler.workspace_root = wr
    LensesHandler.registry = {}
    LensesHandler.expected_github_login = None
    LensesHandler.session_manager = SessionManager(wr)

    server = ThreadingHTTPServer(("127.0.0.1", 0), LensesHandler)
    port = server.server_address[1]
    th = threading.Thread(target=server.serve_forever, daemon=True)
    th.start()
    try:
        yield port, wr
    finally:
        server.shutdown()
        server.server_close()
        th.join(timeout=10)


def _post_json(port: int, path: str, body: dict) -> tuple[int, dict]:
    c = HTTPConnection("127.0.0.1", port)
    payload = json.dumps(body).encode("utf-8")
    c.request(
        "POST",
        path,
        body=payload,
        headers={"Content-Type": "application/json", "Content-Length": str(len(payload))},
    )
    resp = c.getresponse()
    raw = resp.read().decode("utf-8")
    c.close()
    try:
        parsed = json.loads(raw) if raw else {}
    except json.JSONDecodeError:
        parsed = {"_raw": raw}
    return resp.status, parsed if isinstance(parsed, dict) else {}


@pytest.mark.parametrize("case", load_question_bank()[:3], ids=lambda c: c.id)
def test_copilot_question_bank_http_sync_mock(copilot_http_server, case) -> None:
    """HTTP headless path — sync chat endpoint, mocked LLM (no Studio, no SSE)."""
    port, _wr = copilot_http_server
    body: dict = {
        "provider": "ollama",
        "message": case.message,
        "refine": False,
        "tool_mode": "read_only",
        "route": case.route,
        "studio_task_id": "search_knowledge",
        "stream": False,
    }
    if case.project_slug:
        body["project_slug"] = case.project_slug
    if case.scope_site:
        body["scope_site"] = case.scope_site
    if case.page_context_summary:
        body["page_context_summary"] = case.page_context_summary
    if case.related_md_rel_paths:
        body["related_md_rel_paths"] = case.related_md_rel_paths

    status, res = _post_json(port, "/api/sdlc-copilot/chat", body)
    assert status == 200
    verdict = evaluate_orchestration(case, res)
    assert verdict.passed, verdict.summary()
