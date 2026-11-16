"""Grounded copilot chat: retrieval + LLM + optional tool proposals + audit."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Callable

from lenses import llm_chat

from lenses.sdlc_copilot.audit import log_chat_turn, new_audit_id
from lenses.sdlc_copilot.drafts import build_tool_proposals, persist_proposals
from lenses.sdlc_copilot.feature_flag import experimental_sdlc_copilot_enabled
from lenses.sdlc_copilot.grounding import build_grounding_bundle
from lenses.sdlc_copilot.intent import classify_copilot_strategy, map_reduce_enabled
from lenses.sdlc_copilot.map_reduce import run_copilot_map_reduce
from lenses.sdlc_copilot.turn_reflection import build_turn_reflection, reply_deflects_despite_sources

EmitFn = Callable[[str, dict[str, Any]], None] | None


def parse_sdlc_copilot_request_body(body: dict[str, Any]) -> dict[str, Any]:
    """Shared POST body parsing for /api/sdlc-copilot/chat and chat-async."""
    provider = str(body.get("provider", "")).strip()
    message = str(body.get("message", ""))
    model_raw = body.get("model")
    if model_raw is None:
        model_override: str | None = None
    else:
        ms = str(model_raw).strip()
        model_override = ms if ms else None
    refine = bool(body.get("refine"))
    stid_raw = body.get("studio_task_id")
    studio_task_id = str(stid_raw).strip() if stid_raw is not None else None
    studio_task_id = studio_task_id if studio_task_id else "search_knowledge"
    tool_mode = str(body.get("tool_mode") or "read_only").strip()
    route = str(body.get("route") or "")
    project_raw = body.get("project_slug") or body.get("project")
    if project_raw is None:
        project_slug: str | None = None
    else:
        ps = str(project_raw).strip()
        project_slug = ps if ps else None
    entity_raw = body.get("entity_id")
    entity_id = str(entity_raw).strip() if entity_raw is not None else None
    entity_id = entity_id if entity_id else None
    site_raw = body.get("scope_site") or body.get("repo") or body.get("site")
    scope_site = str(site_raw).strip() if site_raw is not None else ""

    page_ctx_raw = body.get("page_context_summary")
    if page_ctx_raw is None:
        page_context_summary: str | None = None
    else:
        pcs = str(page_ctx_raw).strip()
        page_context_summary = pcs[:3000] if pcs else None

    raw_mdp = body.get("related_md_rel_paths")
    related_md_rel_paths: list[str] | None = None
    if isinstance(raw_mdp, list):
        acc_mdp: list[str] = []
        for item in raw_mdp[:12]:
            if isinstance(item, str):
                t = item.strip()
                if len(t) > 512:
                    t = t[:512]
                if t:
                    acc_mdp.append(t)
        if acc_mdp:
            related_md_rel_paths = acc_mdp

    scm_raw = body.get("studio_chat_mode")
    studio_chat_mode = str(scm_raw).strip() if scm_raw is not None else None
    if studio_chat_mode == "":
        studio_chat_mode = None

    cmr = body.get("copilot_max_rounds")
    copilot_max_rounds: int | None = None
    if cmr is not None:
        try:
            v = int(cmr)
            if 1 <= v <= 5:
                copilot_max_rounds = v
        except (TypeError, ValueError):
            pass

    # Client hint: use async + SSE (default True). When False, client should POST /chat instead of chat-async.
    stream_raw = body.get("stream")
    use_stream = True if stream_raw is None else bool(stream_raw)

    return {
        "provider": provider,
        "message": message,
        "model_override": model_override,
        "refine": refine,
        "studio_task_id": studio_task_id,
        "tool_mode": tool_mode,
        "route": route,
        "project_slug": project_slug,
        "entity_id": entity_id,
        "scope_site": scope_site,
        "page_context_summary": page_context_summary,
        "related_md_rel_paths": related_md_rel_paths,
        "studio_chat_mode": studio_chat_mode,
        "copilot_max_rounds": copilot_max_rounds,
        "stream": use_stream,
    }


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


def _default_max_rounds(requested: int | None) -> int:
    if requested is not None and 1 <= int(requested) <= 5:
        return int(requested)
    raw = (os.environ.get("LENSES_COPILOT_MAX_ROUNDS") or "").strip()
    if raw.isdigit():
        v = int(raw)
        if 1 <= v <= 5:
            return v
    return 3


def _git_count_from_scan(scan_state: dict[str, Any]) -> int:
    children = scan_state.get("children") if isinstance(scan_state, dict) else None
    if not isinstance(children, list):
        return 0
    return sum(1 for ch in children if isinstance(ch, dict) and ch.get("is_git"))


def _maybe_map_reduce(
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
    studio_task_id: str | None,
    page_context_summary: str | None,
    related_md_rel_paths: list[str] | None,
    studio_chat_mode: str | None,
    on_event: EmitFn = None,
) -> dict[str, Any] | None:
    strategy = classify_copilot_strategy(
        user_message,
        studio_route=route,
        scan_state=scan_state,
    )
    git_n = _git_count_from_scan(scan_state)
    if strategy == "single_shot" or not map_reduce_enabled(strategy, git_n):
        return None
    return run_copilot_map_reduce(
        workspace_root=workspace_root,
        provider=provider,
        user_message=user_message,
        model_override=model_override,
        refine=refine,
        tool_mode=tool_mode,
        route=route,
        project_slug=project_slug,
        entity_id=entity_id,
        scope_site=scope_site,
        login=login,
        scan_state=scan_state,
        strategy=strategy,
        studio_task_id=studio_task_id,
        page_context_summary=page_context_summary,
        related_md_rel_paths=related_md_rel_paths,
        studio_chat_mode=studio_chat_mode,
        on_event=on_event,
    )


def _run_copilot_chat_pass(
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
    studio_task_id: str | None = None,
    page_context_summary: str | None = None,
    related_md_rel_paths: list[str] | None = None,
    studio_chat_mode: str | None = None,
    max_citations_start: int = 48,
    page_context_append: str | None = None,
    skip_tool_proposals: bool = False,
) -> dict[str, Any]:
    """Single grounding + LLM + audit pass (internal)."""
    if not experimental_sdlc_copilot_enabled():
        return {"ok": False, "error": "feature_disabled"}

    tm = (tool_mode or "read_only").strip()
    if tm not in ("read_only", "propose_writes"):
        return {"ok": False, "error": "invalid_tool_mode", "detail": tm}

    audit_id = new_audit_id()
    msg = (user_message or "").strip()
    if not msg:
        return {"ok": False, "error": "missing_message"}

    pcs_effective = (page_context_summary or "").strip()
    scm = (studio_chat_mode or "").strip().lower()
    if scm == "threads":
        line = (
            "[Studio UI] The operator has Forge Studio **Chat** open in **Threads** mode "
            "(one persisted conversation per Studio route; navigating changes the active thread). "
            "Answer factual questions about this mode directly when asked."
        )
        pcs_effective = f"{pcs_effective}\n\n{line}" if pcs_effective else line
    elif scm in ("linear", "linear_chat", "chat"):
        line = (
            "[Studio UI] The operator has Forge Studio **Chat** open in **linear Chat** mode "
            "(multi-turn stream with page-source hints on each user line)."
        )
        pcs_effective = f"{pcs_effective}\n\n{line}" if pcs_effective else line

    append = (page_context_append or "").strip()
    if append:
        pcs_effective = f"{pcs_effective}\n\n{append}" if pcs_effective else append

    grounding_truncated = False
    citations: list[dict[str, Any]] = []
    block = ""
    max_cit = max(8, int(max_citations_start))
    while max_cit >= 8:
        block, citations, gflag = build_grounding_bundle(
            workspace_root,
            msg,
            scan_state=scan_state,
            scope_site=scope_site,
            focus_entity_id=(entity_id or "").strip() or None,
            max_citations=max_cit,
            page_context_summary=pcs_effective or None,
            related_md_rel_paths=related_md_rel_paths,
            studio_route=route,
        )
        grounding_truncated = grounding_truncated or gflag
        composed = f"{block}\n\n--- USER QUESTION ---\n{msg}"
        if len(composed) <= llm_chat.MAX_MESSAGE_CHARS:
            break
        max_cit -= 8
    else:
        room = llm_chat.MAX_MESSAGE_CHARS - len(msg) - 100
        if room < 1500:
            room = 1500
        block = block[:room] + "\n\n[GROUNDING TRUNCATED FOR SIZE]\n"
        grounding_truncated = True
        composed = f"{block}\n\n--- USER QUESTION ---\n{msg}"

    result = llm_chat.chat(
        provider,
        composed,
        model_override,
        workspace_root=workspace_root,
        refine=refine,
        studio_task_id=studio_task_id,
    )

    proposals: list[dict[str, Any]] = []
    if tm == "propose_writes" and not skip_tool_proposals:
        raw = build_tool_proposals(msg, workspace_root, scan_state)
        if raw:
            proposals = persist_proposals(
                workspace_root,
                raw,
                audit_id=audit_id,
                login=login,
                project_slug=project_slug,
            )

    err = None
    if not result.get("ok"):
        err = str(result.get("error") or "error")

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
        citation_count=len(citations),
        response_ok=bool(result.get("ok")),
        error=err,
        proposals_count=len(proposals),
    )

    try:
        from lenses.governance.audit_log import KIND_AI_ACTION, append_event

        append_event(
            workspace_root,
            kind=KIND_AI_ACTION,
            actor=login,
            resource="sdlc-copilot:chat",
            project_slug=project_slug,
            detail={
                "audit_id": audit_id,
                "route": route,
                "tool_mode": tm,
                "provider": provider,
                "ok": bool(result.get("ok")),
                "citations": len(citations),
                "proposals": len(proposals),
            },
        )
    except OSError:
        pass

    out = dict(result)
    out["citations"] = citations
    out["audit_id"] = audit_id
    out["grounding_truncated"] = grounding_truncated
    out["write_proposals"] = proposals
    out["tool_mode"] = tm
    if bool(result.get("ok")) and str(result.get("text") or "").strip():
        out["turn_reflection"] = build_turn_reflection(
            user_message=msg,
            assistant_text=str(result.get("text") or ""),
            citation_count=len(citations),
            grounding_truncated=grounding_truncated,
            workspace_root=workspace_root,
            provider=provider,
            model_override=model_override,
            citations=citations,
        )
    return out


def run_copilot_chat(
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
    studio_task_id: str | None = None,
    page_context_summary: str | None = None,
    related_md_rel_paths: list[str] | None = None,
    studio_chat_mode: str | None = None,
) -> dict[str, Any]:
    """One-shot grounded copilot (backward compatible)."""
    mr = _maybe_map_reduce(
        workspace_root=workspace_root,
        provider=provider,
        user_message=user_message,
        model_override=model_override,
        refine=refine,
        tool_mode=tool_mode,
        route=route,
        project_slug=project_slug,
        entity_id=entity_id,
        scope_site=scope_site,
        login=login,
        scan_state=scan_state,
        studio_task_id=studio_task_id,
        page_context_summary=page_context_summary,
        related_md_rel_paths=related_md_rel_paths,
        studio_chat_mode=studio_chat_mode,
    )
    if mr is not None:
        return mr
    out = _run_copilot_chat_pass(
        workspace_root=workspace_root,
        provider=provider,
        user_message=user_message,
        model_override=model_override,
        refine=refine,
        tool_mode=tool_mode,
        route=route,
        project_slug=project_slug,
        entity_id=entity_id,
        scope_site=scope_site,
        login=login,
        scan_state=scan_state,
        studio_task_id=studio_task_id,
        page_context_summary=page_context_summary,
        related_md_rel_paths=related_md_rel_paths,
        studio_chat_mode=studio_chat_mode,
        max_citations_start=48,
        page_context_append=None,
        skip_tool_proposals=False,
    )
    if out.get("ok") is True:
        out["copilot_trace"] = {
            "rounds": [{"round": 1, "audit_id": out.get("audit_id"), "deflected": False}],
            "stopped_reason": "single_shot",
        }
    return out


def run_copilot_chat_multi(
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
    studio_task_id: str | None = None,
    page_context_summary: str | None = None,
    related_md_rel_paths: list[str] | None = None,
    studio_chat_mode: str | None = None,
    max_rounds: int | None = None,
    on_event: EmitFn = None,
) -> dict[str, Any]:
    """Up to N grounding+LLM rounds; widen context when the model deflects."""
    mr = _maybe_map_reduce(
        workspace_root=workspace_root,
        provider=provider,
        user_message=user_message,
        model_override=model_override,
        refine=refine,
        tool_mode=tool_mode,
        route=route,
        project_slug=project_slug,
        entity_id=entity_id,
        scope_site=scope_site,
        login=login,
        scan_state=scan_state,
        studio_task_id=studio_task_id,
        page_context_summary=page_context_summary,
        related_md_rel_paths=related_md_rel_paths,
        studio_chat_mode=studio_chat_mode,
        on_event=on_event,
    )
    if mr is not None:
        return mr
    cap = _default_max_rounds(max_rounds)
    emit = on_event or (lambda _t, _p: None)
    cumulative: dict[str, int] = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
    trace_rounds: list[dict[str, Any]] = []
    expand_hint: str | None = None
    max_cit_start = 48
    last_out: dict[str, Any] = {"ok": False, "error": "no_rounds"}
    stopped_reason = "error"

    for rnd in range(1, cap + 1):
        emit("round_start", {"round": rnd, "max_rounds": cap})
        emit(
            "thought",
            {"message": f"Grounding and model call (round {rnd} of {cap})…"},
        )
        skip_props = rnd < cap
        out = _run_copilot_chat_pass(
            workspace_root=workspace_root,
            provider=provider,
            user_message=user_message,
            model_override=model_override,
            refine=refine,
            tool_mode=tool_mode,
            route=route,
            project_slug=project_slug,
            entity_id=entity_id,
            scope_site=scope_site,
            login=login,
            scan_state=scan_state,
            studio_task_id=studio_task_id,
            page_context_summary=page_context_summary,
            related_md_rel_paths=related_md_rel_paths,
            studio_chat_mode=studio_chat_mode,
            max_citations_start=max_cit_start,
            page_context_append=expand_hint,
            skip_tool_proposals=skip_props,
        )
        last_out = out
        u = out.get("usage") if isinstance(out.get("usage"), dict) else {}
        cumulative = _usage_add(cumulative, u)
        emit(
            "usage",
            {
                "round": rnd,
                "this_round": dict(u) if u else {},
                "cumulative": dict(cumulative),
            },
        )
        text = str(out.get("text") or "").strip()
        ok = bool(out.get("ok")) and bool(text)
        deflected = ok and reply_deflects_despite_sources(text)
        trace_rounds.append(
            {
                "round": rnd,
                "audit_id": out.get("audit_id"),
                "deflected": deflected,
                "response_ok": bool(out.get("ok")),
                "usage": dict(u) if u else {},
            }
        )
        emit("round_end", {"round": rnd, "deflected": deflected})
        if not ok:
            stopped_reason = "llm_error"
            break
        if not deflected:
            stopped_reason = "answered"
            break
        if rnd >= cap:
            stopped_reason = "max_rounds"
            break
        expand_hint = (
            "[Copilot retry] The previous grounded reply could not answer from the attached context alone. "
            "Broaden retrieval: consider related Studio areas, linked markdown, and handbook-style paths."
        )
        max_cit_start = min(72, max_cit_start + 12)

    if last_out.get("ok") and isinstance(last_out.get("usage"), dict):
        merged = dict(last_out["usage"])
        merged["prompt_tokens"] = cumulative["prompt_tokens"]
        merged["completion_tokens"] = cumulative["completion_tokens"]
        merged["total_tokens"] = cumulative["total_tokens"] or (
            cumulative["prompt_tokens"] + cumulative["completion_tokens"]
        )
        last_out["usage"] = merged
    last_out["copilot_trace"] = {"rounds": trace_rounds, "stopped_reason": stopped_reason}
    return last_out
