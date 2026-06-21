"""Map-reduce Copilot: scoped retrieval per subtask, then synthesis."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Callable

from lenses import llm_chat

from lenses.sdlc_copilot.audit import log_chat_turn, new_audit_id
from lenses.sdlc_copilot.feature_flag import experimental_sdlc_copilot_enabled
from lenses.sdlc_copilot.grounding import build_scoped_grounding_for_subtask
from lenses.sdlc_copilot.intent import CopilotStrategy
from lenses.sdlc_copilot.planner import Plan, Subtask, build_plan
from lenses.sdlc_copilot.turn_reflection import build_turn_reflection

EmitFn = Callable[[str, dict[str, Any]], None] | None


def _usage_add(acc: dict[str, int], u: dict[str, Any] | None) -> dict[str, int]:
    if not u or not isinstance(u, dict):
        return acc
    pt = int(u.get("prompt_tokens") or 0)
    ct = int(u.get("completion_tokens") or 0)
    tt = int(u.get("total_tokens") or 0)
    if tt <= 0 and (pt > 0 or ct > 0):
        tt = pt + ct
    return {
        "prompt_tokens": acc["prompt_tokens"] + pt,
        "completion_tokens": acc["completion_tokens"] + ct,
        "total_tokens": acc["total_tokens"] + tt,
    }


def _renumber_citations(citations: list[dict[str, Any]], offset: int) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for c in citations:
        c2 = dict(c)
        c2["id"] = int(c.get("id") or 0) + offset
        c2["map_slice"] = offset // 20 + 1
        out.append(c2)
    return out


def _build_reduce_prompt(user_message: str, map_results: list[dict[str, Any]], plan: Plan) -> str:
    lines = [
        "You are the Forge Lenses SDLC copilot synthesizing map-phase answers into one final reply.",
        "Use ONLY the map summaries below. Preserve numbering and entry names from the operator question.",
        "Do not invent projects or facts not present in the map summaries.",
        "If map summaries note missing context, carry that honesty into the final answer.",
        "",
        f"--- ORIGINAL QUESTION ---",
        user_message.strip(),
        "",
        "--- MAP SUMMARIES ---",
    ]
    for i, mr in enumerate(map_results, start=1):
        label = str(mr.get("label") or f"slice-{i}")
        text = str(mr.get("text") or "").strip()
        lines.append(f"[Map {i}] {label}")
        lines.append(text if text else "(no answer)")
        lines.append("")
    if plan.truncation_note:
        lines.append(f"Note: {plan.truncation_note}")
        lines.append("")
    lines.append("--- END MAP SUMMARIES ---")
    lines.append("")
    lines.append(
        "Produce the final operator-facing answer (complete sentences, one line per project/entry when requested)."
    )
    return "\n".join(lines)


def run_copilot_map_reduce(
    *,
    workspace_root: Path,
    provider: str,
    user_message: str,
    model_override: str | None,
    refine: bool,
    tool_mode: str,
    route: str,
    project_slug: str | None,
    entity_id: str | None,
    scope_site: str,
    login: str | None,
    scan_state: dict[str, Any],
    strategy: CopilotStrategy,
    studio_task_id: str | None = None,
    page_context_summary: str | None = None,
    related_md_rel_paths: list[str] | None = None,
    studio_chat_mode: str | None = None,
    on_event: EmitFn = None,
) -> dict[str, Any]:
    """Execute plan → map LLM calls → reduce synthesis."""
    emit = on_event or (lambda _t, _p: None)
    if not experimental_sdlc_copilot_enabled():
        return {"ok": False, "error": "feature_disabled"}

    msg = (user_message or "").strip()
    if not msg:
        return {"ok": False, "error": "missing_message"}

    plan = build_plan(
        strategy=strategy,
        workspace_root=workspace_root,
        user_message=msg,
        scan_state=scan_state,
        studio_route=route,
        page_context_summary=page_context_summary,
    )
    if plan is None or not plan.subtasks:
        return {"ok": False, "error": "empty_map_plan"}

    emit(
        "plan",
        {
            "strategy": plan.strategy,
            "subtask_count": len(plan.subtasks),
            "truncated": plan.truncated,
            "note": plan.truncation_note,
        },
    )
    emit(
        "thought",
        {"message": f"Planning {len(plan.subtasks)} scoped lookups ({plan.strategy})…"},
    )

    audit_id = new_audit_id()
    cumulative: dict[str, int] = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
    map_results: list[dict[str, Any]] = []
    all_citations: list[dict[str, Any]] = []
    cit_offset = 0
    grounding_truncated = plan.truncated
    total = len(plan.subtasks)

    for idx, st in enumerate(plan.subtasks, start=1):
        emit(
            "subtask_start",
            {"index": idx, "total": total, "label": st.label, "subtask_id": st.subtask_id},
        )
        block, citations, gflag = build_scoped_grounding_for_subtask(
            workspace_root,
            scan_state=scan_state,
            scope_site=st.scope_site,
            related_md_rel_paths=st.related_md_rel_paths,
            fts_query=st.fts_query,
            max_citations=st.max_citations,
            studio_route=route,
        )
        grounding_truncated = grounding_truncated or gflag
        renorm = _renumber_citations(citations, cit_offset)
        cit_offset += len(citations)
        all_citations.extend(renorm)

        composed = f"{block}\n\n--- MAP TASK ---\n{st.user_sub_prompt}"
        if len(composed) > llm_chat.MAX_MESSAGE_CHARS:
            composed = composed[: llm_chat.MAX_MESSAGE_CHARS - 80] + "\n\n[MAP CONTEXT TRUNCATED]\n"
            grounding_truncated = True

        map_out = llm_chat.chat(
            provider,
            composed,
            model_override,
            workspace_root=workspace_root,
            refine=refine,
            studio_task_id=studio_task_id or "search_knowledge",
        )
        u = map_out.get("usage") if isinstance(map_out.get("usage"), dict) else {}
        cumulative = _usage_add(cumulative, u)
        emit(
            "usage",
            {
                "phase": "map",
                "subtask": idx,
                "this_round": dict(u) if u else {},
                "cumulative": dict(cumulative),
            },
        )

        text = str(map_out.get("text") or "").strip()
        ok = bool(map_out.get("ok")) and bool(text)
        map_results.append(
            {
                "subtask_id": st.subtask_id,
                "label": st.label,
                "repo_names": list(st.repo_names),
                "ok": ok,
                "text": text,
                "error": map_out.get("error"),
            }
        )
        emit(
            "subtask_end",
            {"index": idx, "total": total, "label": st.label, "ok": ok},
        )
        if not ok:
            emit("thought", {"message": f"Map step {idx} failed; continuing with remaining entries…"})

    emit("thought", {"message": "Synthesizing final answer from map summaries…"})
    reduce_prompt = _build_reduce_prompt(msg, map_results, plan)
    reduce_out = llm_chat.chat(
        provider,
        reduce_prompt,
        model_override,
        workspace_root=workspace_root,
        refine=refine,
        studio_task_id=studio_task_id or "search_knowledge",
    )
    ru = reduce_out.get("usage") if isinstance(reduce_out.get("usage"), dict) else {}
    cumulative = _usage_add(cumulative, ru)
    emit(
        "usage",
        {
            "phase": "reduce",
            "this_round": dict(ru) if ru else {},
            "cumulative": dict(cumulative),
        },
    )

    tm = (tool_mode or "read_only").strip()
    log_chat_turn(
        workspace_root,
        audit_id=audit_id,
        kind="chat_turn",
        tool_mode=tm,
        route=route,
        project_slug=project_slug,
        entity_id=entity_id,
        login=login,
        provider=provider,
        user_message_excerpt=msg[:500],
        citation_count=len(all_citations),
        response_ok=bool(reduce_out.get("ok")),
        error=str(reduce_out.get("error") or "") or None,
        proposals_count=0,
    )

    out = dict(reduce_out)
    out["citations"] = all_citations
    out["audit_id"] = audit_id
    out["grounding_truncated"] = grounding_truncated
    out["write_proposals"] = []
    out["tool_mode"] = tm
    if reduce_out.get("ok") and str(reduce_out.get("text") or "").strip():
        out["turn_reflection"] = build_turn_reflection(
            user_message=msg,
            assistant_text=str(reduce_out.get("text") or ""),
            citation_count=len(all_citations),
            grounding_truncated=grounding_truncated,
            workspace_root=workspace_root,
            provider=provider,
            model_override=model_override,
            citations=all_citations,
        )
    if isinstance(out.get("usage"), dict):
        merged = dict(out["usage"])
        merged["prompt_tokens"] = cumulative["prompt_tokens"]
        merged["completion_tokens"] = cumulative["completion_tokens"]
        merged["total_tokens"] = cumulative["total_tokens"] or (
            cumulative["prompt_tokens"] + cumulative["completion_tokens"]
        )
        out["usage"] = merged

    out["copilot_trace"] = {
        "strategy": plan.strategy,
        "stopped_reason": "map_reduce",
        "map_results_count": len(map_results),
        "subtask_count": len(plan.subtasks),
        "truncated": plan.truncated,
        "truncation_note": plan.truncation_note,
        "map_results": [
            {"label": m.get("label"), "ok": m.get("ok"), "repos": m.get("repo_names")}
            for m in map_results
        ],
    }
    return out
