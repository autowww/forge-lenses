"""Headless Copilot question-bank harness (no Studio UI).

Loads ``tests/fixtures/copilot_question_bank/questions.yaml``, runs the Lenses
SDLC copilot engine (grounding → strategy/plan → LLM), and scores answers with
heuristics and an optional LLM judge.
"""

from __future__ import annotations

import json
import os
import re
import shutil
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

ROOT = Path(__file__).resolve().parents[1]
FIXTURE_ROOT = ROOT / "tests" / "fixtures" / "copilot_question_bank"
QUESTIONS_PATH = FIXTURE_ROOT / "questions.yaml"
WORKSPACE_SRC = FIXTURE_ROOT / "workspace"


@dataclass
class CopilotQuestionCase:
    id: str
    description: str
    route: str
    message: str
    scope_site: str = ""
    project_slug: str = ""
    page_context_summary: str = ""
    related_md_rel_paths: list[str] = field(default_factory=list)
    expect: dict[str, Any] = field(default_factory=dict)


@dataclass
class EvalVerdict:
    passed: bool
    reasons: list[str] = field(default_factory=list)
    orchestration: dict[str, Any] = field(default_factory=dict)
    judge_source: str = "none"

    def summary(self) -> str:
        status = "PASS" if self.passed else "FAIL"
        body = "; ".join(self.reasons) if self.reasons else "ok"
        return f"{status}: {body}"


def load_question_bank(path: Path | None = None) -> list[CopilotQuestionCase]:
    import yaml

    p = path or QUESTIONS_PATH
    raw = yaml.safe_load(p.read_text(encoding="utf-8"))
    cases: list[CopilotQuestionCase] = []
    for row in raw.get("cases") or []:
        if not isinstance(row, dict):
            continue
        cid = str(row.get("id") or "").strip()
        if not cid:
            continue
        rel = row.get("related_md_rel_paths")
        rel_list: list[str] = []
        if isinstance(rel, list):
            rel_list = [str(x).strip() for x in rel if str(x).strip()]
        cases.append(
            CopilotQuestionCase(
                id=cid,
                description=str(row.get("description") or "").strip(),
                route=str(row.get("route") or "overview").strip(),
                message=str(row.get("message") or "").strip(),
                scope_site=str(row.get("scope_site") or "").strip(),
                project_slug=str(row.get("project_slug") or "").strip(),
                page_context_summary=str(row.get("page_context_summary") or "").strip(),
                related_md_rel_paths=rel_list,
                expect=row.get("expect") if isinstance(row.get("expect"), dict) else {},
            )
        )
    return cases


def materialize_question_bank_workspace(dest: Path) -> Path:
    """Copy the mini workspace fixture into ``dest`` (writable) and init git repos."""
    import subprocess

    dest = dest.resolve()
    if dest.exists():
        shutil.rmtree(dest)
    shutil.copytree(WORKSPACE_SRC, dest)
    for name in ("alpha", "beta"):
        repo = dest / name
        if repo.is_dir():
            subprocess.run(
                ["git", "init"],
                cwd=repo,
                check=True,
                capture_output=True,
                text=True,
            )
    return dest


def scan_state_for_workspace(workspace_root: Path) -> dict[str, Any]:
    from lenses.scan import scan_workspace

    lenses_root = ROOT
    return scan_workspace(workspace_root, lenses_root, {})


def _orch_expect(case: CopilotQuestionCase) -> dict[str, Any]:
    exp = case.expect.get("orchestration")
    return exp if isinstance(exp, dict) else {}


def _quality_expect(case: CopilotQuestionCase) -> dict[str, Any]:
    exp = case.expect.get("quality")
    return exp if isinstance(exp, dict) else {}


def evaluate_orchestration(case: CopilotQuestionCase, result: dict[str, Any]) -> EvalVerdict:
    """Deterministic checks on copilot_trace, citations, and grounding flags."""
    exp = _orch_expect(case)
    reasons: list[str] = []
    trace = result.get("copilot_trace") if isinstance(result.get("copilot_trace"), dict) else {}
    citations = result.get("citations") if isinstance(result.get("citations"), list) else []
    kinds = [str(c.get("kind") or "") for c in citations if isinstance(c, dict)]

    if exp.get("strategy"):
        want = str(exp["strategy"])
        got = str(trace.get("strategy") or "single_shot")
        if got != want:
            reasons.append(f"strategy want={want} got={got}")

    min_cit = int(exp.get("min_citations") or 0)
    if min_cit and len(citations) < min_cit:
        reasons.append(f"citations {len(citations)} < {min_cit}")

    min_sub = int(exp.get("min_subtasks") or 0)
    if min_sub:
        got_sub = int(trace.get("subtask_count") or 0)
        if got_sub < min_sub:
            reasons.append(f"subtasks {got_sub} < {min_sub}")

    any_kinds = exp.get("citation_kinds_any")
    if isinstance(any_kinds, list) and any_kinds:
        if not any(k in kinds for k in any_kinds):
            reasons.append(f"missing citation kinds any-of {any_kinds}; got {kinds[:8]}")

    if exp.get("skip_roster") and "workspace_projects_roster" in kinds:
        reasons.append("workspace roster present on focused repo case")

    if not result.get("ok"):
        reasons.insert(0, f"copilot ok=false error={result.get('error') or 'unknown'}")

    return EvalVerdict(passed=not reasons, reasons=reasons, orchestration=dict(trace), judge_source="orchestration")


def evaluate_quality_heuristic(case: CopilotQuestionCase, result: dict[str, Any]) -> EvalVerdict:
    exp = _quality_expect(case)
    if not exp:
        return EvalVerdict(passed=True, reasons=[], judge_source="heuristic_skip")

    text = str(result.get("text") or "").strip()
    reasons: list[str] = []
    if not text:
        reasons.append("empty assistant text")

    min_chars = int(exp.get("min_response_chars") or 0)
    if min_chars and len(text) < min_chars:
        reasons.append(f"response length {len(text)} < {min_chars}")

    lower = text.lower()
    for term in exp.get("must_mention") or []:
        t = str(term).strip()
        if t and t.lower() not in lower:
            reasons.append(f"missing mention: {t}")

    for term in exp.get("must_not_mention") or []:
        t = str(term).strip()
        if t and t.lower() in lower:
            reasons.append(f"forbidden mention: {t}")

    return EvalVerdict(passed=not reasons, reasons=reasons, judge_source="heuristic")


def _extract_json_object(raw: str) -> dict[str, Any] | None:
    t = (raw or "").strip()
    if not t:
        return None
    try:
        obj = json.loads(t)
        return obj if isinstance(obj, dict) else None
    except json.JSONDecodeError:
        pass
    m = re.search(r"\{[\s\S]*\}", t)
    if not m:
        return None
    try:
        obj = json.loads(m.group(0))
        return obj if isinstance(obj, dict) else None
    except json.JSONDecodeError:
        return None


def evaluate_quality_llm_judge(
    case: CopilotQuestionCase,
    result: dict[str, Any],
    *,
    provider: str,
    workspace_root: Path,
    model_override: str | None = None,
) -> EvalVerdict:
    """Optional second LLM pass — grades answer against rubric (live tier only)."""
    from lenses import llm_chat

    rubric = str(_quality_expect(case).get("rubric") or "").strip()
    if not rubric:
        return EvalVerdict(passed=True, reasons=[], judge_source="llm_skip")

    text = str(result.get("text") or "").strip()
    citations = result.get("citations") if isinstance(result.get("citations"), list) else []
    prompt = (
        "You grade a Forge Lenses Copilot answer. Reply with JSON only:\n"
        '{"pass": true|false, "reason": "one sentence"}\n\n'
        f"Operator question: {case.message}\n"
        f"Studio route: {case.route}\n"
        f"Scope site: {case.scope_site or '(none)'}\n"
        f"Rubric:\n{rubric}\n\n"
        f"Copilot answer ({len(text)} chars, {len(citations)} citations):\n{text[:6000]}\n"
    )
    out = llm_chat.chat(
        provider,
        prompt,
        model_override,
        workspace_root=workspace_root,
        refine=False,
        studio_task_id="search_knowledge",
    )
    if not out.get("ok"):
        return EvalVerdict(
            passed=False,
            reasons=[f"judge LLM failed: {out.get('error') or 'error'}"],
            judge_source="llm_error",
        )
    parsed = _extract_json_object(str(out.get("text") or ""))
    if not parsed:
        return EvalVerdict(passed=False, reasons=["judge returned non-JSON"], judge_source="llm")
    ok = parsed.get("pass") is True
    reason = str(parsed.get("reason") or ("pass" if ok else "fail")).strip()
    return EvalVerdict(passed=ok, reasons=[] if ok else [reason], judge_source="llm")


def run_copilot_case(
    case: CopilotQuestionCase,
    *,
    workspace_root: Path,
    scan_state: dict[str, Any],
    provider: str = "ollama",
    model_override: str | None = None,
    use_multi: bool = True,
    on_event: Callable[[str, dict[str, Any]], None] | None = None,
) -> dict[str, Any]:
    """Run one question through the same engine entrypoint as ``/api/sdlc-copilot/chat``."""
    from lenses.sdlc_copilot.chat import run_copilot_chat, run_copilot_chat_multi

    common = dict(
        workspace_root=workspace_root,
        provider=provider,
        user_message=case.message,
        model_override=model_override,
        refine=False,
        tool_mode="read_only",
        route=case.route,
        project_slug=case.project_slug or None,
        entity_id=None,
        scope_site=case.scope_site,
        login=None,
        scan_state=scan_state,
        page_context_summary=case.page_context_summary or None,
        related_md_rel_paths=case.related_md_rel_paths or None,
    )
    if use_multi:
        return run_copilot_chat_multi(**common, max_rounds=3, on_event=on_event)
    return run_copilot_chat(**common)


def make_grounding_aware_mock_chat() -> Callable[..., dict[str, Any]]:
    """Mock LLM that returns plausible text keyed off grounding / map-reduce phases."""

    def fake_chat(
        provider: str,
        composed: str,
        model_override: str | None = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        msg = composed or ""
        usage = {"prompt_tokens": 12, "completion_tokens": 8, "total_tokens": 20}
        lower = msg.lower()

        if "--- map task ---" in lower or "map task" in lower:
            if "alpha" in lower:
                return {
                    "ok": True,
                    "text": "Alpha is a demo payments API service. [1]",
                    "model": "mock-map",
                    "usage": usage,
                }
            if "beta" in lower:
                return {
                    "ok": True,
                    "text": "Beta is documentation tooling for handbook builds. [1]",
                    "model": "mock-map",
                    "usage": usage,
                }
            return {"ok": True, "text": "Scoped repo summary line. [1]", "model": "mock-map", "usage": usage}

        if "map summaries" in lower or "original question" in lower:
            return {
                "ok": True,
                "text": (
                    "1. **alpha** — demo payments API service.\n"
                    "2. **beta** — documentation tooling and handbook generators."
                ),
                "model": "mock-reduce",
                "usage": usage,
            }

        if "repository alpha" in lower or "alpha/readme" in lower or "scope_site: alpha" in lower:
            return {
                "ok": True,
                "text": (
                    "This repository (**alpha**) is a demo **payments** API service "
                    "with checkout and ledger endpoints for integration tests."
                ),
                "model": "mock",
                "usage": usage,
            }
        if "repository beta" in lower or "beta/readme" in lower:
            return {
                "ok": True,
                "text": (
                    "This repository (**beta**) provides **documentation** tooling: "
                    "generators, handbook builds, and static-site helpers."
                ),
                "model": "mock",
                "usage": usage,
            }
        if "charge" in lower and "alpha" in lower:
            return {
                "ok": True,
                "text": "The alpha charge log lives at alpha/forge/charge.md in this workspace.",
                "model": "mock",
                "usage": usage,
            }
        if "projects" in lower and ("alpha" in lower or "beta" in lower):
            return {
                "ok": True,
                "text": "This workspace contains **alpha** (payments demo) and **beta** (documentation tooling).",
                "model": "mock",
                "usage": usage,
            }
        return {
            "ok": True,
            "text": "Grounded workspace answer with citation [1].",
            "model": "mock",
            "usage": usage,
        }

    return fake_chat


def live_env_enabled() -> bool:
    return os.environ.get("LENSES_COPILOT_LIVE", "").strip().lower() in ("1", "true", "yes", "on")


def live_provider() -> str:
    return (os.environ.get("LENSES_COPILOT_LIVE_PROVIDER") or "openai_compatible").strip()


def live_model_override() -> str | None:
    raw = (os.environ.get("LENSES_COPILOT_LIVE_MODEL") or "").strip()
    return raw or None


def live_judge_enabled() -> bool:
    raw = (os.environ.get("LENSES_COPILOT_JUDGE") or "1").strip().lower()
    return raw not in ("0", "false", "no", "off")


def resolve_workspace_for_run(tmp_path: Path) -> Path:
    override = (os.environ.get("LENSES_COPILOT_WORKSPACE") or "").strip()
    if override:
        p = Path(override).expanduser().resolve()
        if p.is_dir():
            return p
    return materialize_question_bank_workspace(tmp_path / "copilot-qb-ws")
