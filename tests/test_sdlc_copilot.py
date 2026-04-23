"""Tests for grounded SDLC copilot (no network)."""

from __future__ import annotations

from pathlib import Path
import pytest

from lenses import llm_chat
from lenses.access_policy import load_policy, save_policy
from lenses.sdlc_copilot import commit_stored_proposal, experimental_sdlc_copilot_enabled
from lenses.sdlc_copilot.chat import run_copilot_chat
from lenses.sdlc_copilot.drafts import build_tool_proposals, persist_proposals
from lenses.sdlc_copilot.feature_flag import experimental_sdlc_copilot_enabled as flag_fn
from lenses.sdlc_copilot.grounding import build_grounding_bundle, search_query_for_grounding
from lenses.sdlc_copilot.permissions import may_use_propose_writes


def test_feature_flag_default_on() -> None:
    assert experimental_sdlc_copilot_enabled() is True


def test_feature_flag_off(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LENSES_EXPERIMENTAL_SDLC_COPILOT", "0")
    # Re-import to pick up env in same process — read from os in function
    assert flag_fn() is False


def test_grounding_bundle_empty_workspace(tmp_path: Path) -> None:
    block, citations, trunc = build_grounding_bundle(
        tmp_path,
        "orchestration release quality",
        scan_state={"children": [], "resolved_at": None},
        max_citations=20,
    )
    assert "--- CONTEXT ---" in block
    assert isinstance(citations, list)
    assert trunc is False


def test_search_query_docs_health_vague_uses_anchor() -> None:
    q = search_query_for_grounding(
        "what's important on this page?",
        studio_route="docs-health",
        scope_site="forgesdlc-kitchensink",
    )
    assert "forgesdlc-kitchensink" in q
    assert "documentation" in q
    assert "health" in q


def test_search_query_non_docs_route_no_health_anchor() -> None:
    q = search_query_for_grounding(
        "what is important on this page?",
        studio_route="overview",
        scope_site="forgesdlc-kitchensink",
    )
    assert "documentation" not in q.lower()


def test_grounding_docs_health_skips_workspace_rollups(tmp_path: Path) -> None:
    block, citations, trunc = build_grounding_bundle(
        tmp_path,
        "what matters on this screen",
        scan_state={"children": [], "resolved_at": None},
        max_citations=40,
        studio_route="docs-health",
        scope_site="acme-repo",
        page_context_summary="Forge Studio · Docs health · acme-repo\n\nOn-screen: score + findings.",
    )
    kinds = [c.get("kind") for c in citations]
    assert trunc is False
    assert "test_quality" not in kinds
    assert "devsecops" not in kinds
    assert "llm_usage_events" not in kinds
    assert "studio_page_context" in kinds
    assert "Context: the operator is on a Forge Studio **Docs health** view" in block


def test_grounding_bundle_page_context_and_related_md(tmp_path: Path) -> None:
    md_dir = tmp_path / "forge"
    md_dir.mkdir(parents=True)
    charge = md_dir / "charge.md"
    charge.write_text("# Charge\nHello from charge.\n", encoding="utf-8")
    block, citations, trunc = build_grounding_bundle(
        tmp_path,
        "what changed",
        scan_state={"children": [], "resolved_at": None},
        max_citations=30,
        page_context_summary="Forge Studio · Plan · repo demo",
        related_md_rel_paths=["forge/charge.md", "nope/bad.md"],
    )
    assert trunc is False
    kinds = [c.get("kind") for c in citations]
    assert "studio_page_context" in kinds
    assert "related_workspace_md" in kinds
    md_cits = [c for c in citations if c.get("kind") == "related_workspace_md"]
    assert md_cits and "Hello from charge" in (md_cits[0].get("snippet") or "")
    assert citations[0].get("kind") == "studio_page_context"


def test_propose_writes_policy_enforced_requires_project(tmp_path: Path) -> None:
    save_policy(
        tmp_path,
        {
            "bootstrap_completed": True,
            "policy_enabled": True,
            "super_admins": [],
            "projects": {
                "acme": {
                    "require_explicit_membership": False,
                    "default_role": "viewer",
                    "members": {"alice": {"role": "member"}},
                }
            },
        },
    )
    pol = load_policy(tmp_path)
    assert may_use_propose_writes(pol, "alice", None) is False
    assert may_use_propose_writes(pol, "alice", "acme") is True


def test_build_tool_proposals_keywords(tmp_path: Path) -> None:
    scan = {"children": [], "resolved_at": None}
    props = build_tool_proposals("Draft a test plan for regression", tmp_path, scan)
    assert any(p.get("tool_id") == "test_plan_draft" for p in props)


def test_copilot_chat_disabled(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("LENSES_EXPERIMENTAL_SDLC_COPILOT", "0")
    r = run_copilot_chat(
        workspace_root=tmp_path,
        provider="ollama",
        user_message="hi",
        model_override=None,
        refine=False,
        tool_mode="read_only",
        route="chat",
        project_slug=None,
        entity_id=None,
        scope_site="",
        login=None,
        scan_state={"children": [], "resolved_at": None},
    )
    assert r.get("ok") is False
    assert r.get("error") == "feature_disabled"


def test_copilot_chat_mock_llm(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.delenv("LENSES_EXPERIMENTAL_SDLC_COPILOT", raising=False)

    def fake_chat(*_a, **_k):
        return {"ok": True, "text": "Answer with [1].", "model": "mock"}

    monkeypatch.setattr(llm_chat, "chat", fake_chat)
    r = run_copilot_chat(
        workspace_root=tmp_path,
        provider="ollama",
        user_message="What is indexed?",
        model_override=None,
        refine=False,
        tool_mode="read_only",
        route="search",
        project_slug=None,
        entity_id=None,
        scope_site="",
        login=None,
        scan_state={"children": [], "resolved_at": None},
    )
    assert r.get("ok") is True
    assert "citations" in r
    assert "audit_id" in r
    assert r.get("write_proposals") == []
    assert isinstance(r.get("turn_reflection"), dict)
    assert isinstance(r.get("copilot_trace"), dict)


def test_commit_proposal_confirm(tmp_path: Path) -> None:
    props = [{"tool_id": "x", "title": "t", "payload": {"a": 1}}]
    saved = persist_proposals(
        tmp_path, props, audit_id="aid", login="bob", project_slug="acme"
    )
    pid = saved[0]["id"]
    r = commit_stored_proposal(tmp_path, pid, login="bob", confirm=False)
    assert r.get("ok") is False

    r2 = commit_stored_proposal(tmp_path, pid, login="bob", confirm=True)
    assert r2.get("ok") is True
    assert "export_path" in r2
