"""LLM refinement for Blueprints Wizard Foundation Brief (experimental)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from lenses.blueprints_wizard.schemas import WizardSessionDocument
from lenses.blueprints_wizard.session_store import load_session, save_session_replace, validate_session_id

# Keep prompt compact; full methodology text lives in Blueprints / handbook.
_REFINE_INSTRUCTIONS = """You are helping draft a short **Foundation Brief** for a Forge Blueprints–aligned initiative.

Given the user's wizard notes below, produce **Markdown** with these sections (use headings):
1. **Problem / outcome** — what success looks like
2. **Constraints** — time, scope, dependencies (if inferable)
3. **Stakeholders / audience** (if inferable)
4. **Risks / unknowns**

If notes are empty or too vague, say what is missing in a short bullet list instead of inventing facts.

--- Wizard notes ---

"""


def _mission_markdown(payload: dict[str, Any]) -> str:
    """Structured Mission step (payload.mission) — mirrors Studio wizard step 0."""
    m = payload.get("mission")
    if not isinstance(m, dict):
        return ""
    parts: list[str] = []
    mode = m.get("mode")
    if isinstance(mode, str) and mode.strip():
        parts.append(f"**Mission mode:** {mode.strip().replace('_', ' ')}")
    title = m.get("title")
    outcome = m.get("outcome")
    notes = m.get("notes")
    if isinstance(title, str) and title.strip():
        parts.append(f"**Mission title:** {title.strip()}")
    if isinstance(outcome, str) and outcome.strip():
        parts.append(f"**Outcome:** {outcome.strip()}")
    if isinstance(notes, str) and notes.strip():
        parts.append(f"**Additional notes:** {notes.strip()}")
    return "\n\n".join(parts).strip()


def _contribution_setup_markdown(payload: dict[str, Any]) -> str:
    """Contribution Setup step (payload.contributionSetup) — Studio wizard step 1."""
    c = payload.get("contributionSetup")
    if not isinstance(c, dict):
        return ""
    parts: list[str] = []
    deliverable = c.get("deliverable")
    landing = c.get("landingPlace")
    notes = c.get("notes")
    if isinstance(deliverable, str) and deliverable.strip():
        parts.append(f"**Deliverable:** {deliverable.strip()}")
    if isinstance(landing, str) and landing.strip():
        parts.append(f"**Landing place:** {landing.strip()}")
    if isinstance(notes, str) and notes.strip():
        parts.append(f"**Notes:** {notes.strip()}")
    return "\n\n".join(parts).strip()


def _context_intake_markdown(payload: dict[str, Any]) -> str:
    """Context Intake step (payload.contextIntake) — Studio wizard step 2."""
    x = payload.get("contextIntake")
    if not isinstance(x, dict):
        return ""
    parts: list[str] = []
    rough = x.get("roughNotes")
    refs = x.get("referenceHints")
    if isinstance(rough, str) and rough.strip():
        parts.append(f"**Rough notes:** {rough.strip()}")
    if isinstance(refs, str) and refs.strip():
        parts.append(f"**References:** {refs.strip()}")
    sf = x.get("sourceFlags")
    if isinstance(sf, dict):
        flags = [k for k, v in sf.items() if v is True]
        if flags:
            parts.append("**Context source flags:** " + ", ".join(flags))
    atts = x.get("attachments")
    if isinstance(atts, list) and atts:
        lines = []
        for a in atts[:32]:
            if not isinstance(a, dict):
                continue
            lab = a.get("label")
            ref = a.get("ref")
            if isinstance(lab, str) and lab.strip():
                lines.append(lab.strip() + (f" ({ref})" if isinstance(ref, str) and ref.strip() else ""))
        if lines:
            parts.append("**Attachments:** " + "; ".join(lines))
    sources = x.get("sources")
    summary = x.get("summary")
    notes = x.get("notes")
    if isinstance(sources, str) and sources.strip():
        parts.append(f"**Sources (legacy):** {sources.strip()}")
    if isinstance(summary, str) and summary.strip():
        parts.append(f"**Summary (legacy):** {summary.strip()}")
    if isinstance(notes, str) and notes.strip():
        parts.append(f"**Notes (legacy):** {notes.strip()}")
    return "\n\n".join(parts).strip()


def _understanding_markdown(payload: dict[str, Any]) -> str:
    """Understanding step (payload.understanding) — Studio wizard step 3."""
    u = payload.get("understanding")
    if not isinstance(u, dict):
        return ""
    parts: list[str] = []
    summary = u.get("summary")
    gaps = u.get("knownGaps")
    if isinstance(summary, str) and summary.strip():
        parts.append(f"**Current understanding:** {summary.strip()}")
    if isinstance(gaps, str) and gaps.strip():
        parts.append(f"**Gaps / unknowns:** {gaps.strip()}")
    return "\n\n".join(parts).strip()


def _clarification_markdown(payload: dict[str, Any]) -> str:
    """Clarification step (payload.clarification) — Studio wizard step 4."""
    c = payload.get("clarification")
    if not isinstance(c, dict):
        return ""
    parts: list[str] = []
    oq = c.get("openQuestions")
    dn = c.get("decisionsNeeded")
    if isinstance(oq, str) and oq.strip():
        parts.append(f"**Open questions:** {oq.strip()}")
    if isinstance(dn, str) and dn.strip():
        parts.append(f"**Decisions needed:** {dn.strip()}")
    return "\n\n".join(parts).strip()


def _target_output_pack_markdown(payload: dict[str, Any]) -> str:
    """Target & Output Pack (payload.targetOutputPack) — Studio wizard step 5."""
    t = payload.get("targetOutputPack")
    if not isinstance(t, dict):
        return ""
    parts: list[str] = []
    stage = t.get("targetStage")
    kind = t.get("outputPackKind")
    plab = t.get("packLabel")
    lines = t.get("artifactLines")
    if isinstance(stage, str) and stage.strip():
        parts.append(f"**Target stage:** {stage.strip().replace('_', ' ')}")
    if isinstance(kind, str) and kind.strip():
        parts.append(f"**Output pack kind:** {kind.strip().replace('_', ' ')}")
    if isinstance(plab, str) and plab.strip():
        parts.append(f"**Output pack label:** {plab.strip()}")
    if isinstance(lines, str) and lines.strip():
        parts.append(f"**Artifact lines:**\n{lines.strip()}")
    return "\n\n".join(parts).strip()


def _autonomy_mutation_markdown(payload: dict[str, Any]) -> str:
    """Autonomy & Mutation (payload.autonomyMutation) — Studio wizard step 6."""
    a = payload.get("autonomyMutation")
    if not isinstance(a, dict):
        return ""
    parts: list[str] = []
    al = a.get("autonomyLevel")
    mp = a.get("mutationPolicy")
    if isinstance(al, str) and al.strip():
        parts.append(f"**Autonomy:** {al.strip().replace('_', ' ')}")
    if isinstance(mp, str) and mp.strip():
        parts.append(f"**Mutation policy:** {mp.strip().replace('_', ' ')}")
    return "\n\n".join(parts).strip()


def _run_plan_markdown(payload: dict[str, Any]) -> str:
    """Run plan (`wizard_domain.run_plan`) — Studio wizard step 8."""
    wd = payload.get("wizard_domain")
    if not isinstance(wd, dict):
        return ""
    rp = wd.get("run_plan")
    if not isinstance(rp, dict):
        return ""
    parts: list[str] = []
    title = rp.get("title")
    if isinstance(title, str) and title.strip():
        parts.append(f"**Title:** {title.strip()}")
    steps = rp.get("steps")
    if isinstance(steps, list) and steps:
        for i, raw in enumerate(steps[:48], start=1):
            if not isinstance(raw, dict):
                continue
            st = raw.get("title")
            det = raw.get("detail")
            head = f"{i}. "
            if isinstance(st, str) and st.strip():
                head += st.strip()
            else:
                head += "(untitled step)"
            parts.append(head)
            if isinstance(det, str) and det.strip():
                parts.append(det.strip())
    return "\n\n".join(parts).strip()


def _scope_selection_markdown(payload: dict[str, Any]) -> str:
    """Scope selection (payload.scopeSelection and wizard_domain.scope_spec) — Studio wizard step 7."""
    parts: list[str] = []
    sel = payload.get("scopeSelection")
    if isinstance(sel, dict):
        b = sel.get("scopeBoundary")
        if isinstance(b, str) and b.strip():
            parts.append(f"**Scope boundary:** {b.strip().replace('_', ' ')}")
        for label, key in (
            ("Milestone", "milestoneRef"),
            ("WBE path", "wbePath"),
            ("Capability", "capabilityLabel"),
            ("Team", "teamLabel"),
            ("Repo paths", "repoPathsText"),
            ("Recheck / stale subset", "recheckIssueRefs"),
        ):
            v = sel.get(key)
            if isinstance(v, str) and v.strip():
                parts.append(f"**{label}:** {v.strip()}")
    wd = payload.get("wizard_domain")
    if isinstance(wd, dict):
        spec = wd.get("scope_spec")
        if isinstance(spec, dict):
            co = spec.get("closure_options")
            if isinstance(co, list) and co:
                parts.append("**Closure options:** " + ", ".join(str(x).replace("_", " ") for x in co if x))
    return "\n\n".join(parts).strip()


def _step_note_redundant_with_structured(k: str, payload: dict[str, Any]) -> bool:
    """Avoid duplicating stepNotes 3–7 when structured payload blocks are present."""
    if k == "3" and _understanding_markdown(payload):
        return True
    if k == "4" and _clarification_markdown(payload):
        return True
    if k == "5" and _target_output_pack_markdown(payload):
        return True
    if k == "6" and _autonomy_mutation_markdown(payload):
        return True
    if k == "7" and _scope_selection_markdown(payload):
        return True
    if k == "8" and _run_plan_markdown(payload):
        return True
    return False


def _notes_markdown(payload: dict[str, Any]) -> str:
    chunks: list[str] = []
    mission_block = _mission_markdown(payload)
    if mission_block:
        chunks.append("**Mission (structured)**\n" + mission_block)
    contrib_block = _contribution_setup_markdown(payload)
    if contrib_block:
        chunks.append("**Contribution Setup (structured)**\n" + contrib_block)
    ctx_block = _context_intake_markdown(payload)
    if ctx_block:
        chunks.append("**Context Intake (structured)**\n" + ctx_block)
    und_block = _understanding_markdown(payload)
    if und_block:
        chunks.append("**Understanding (structured)**\n" + und_block)
    clar_block = _clarification_markdown(payload)
    if clar_block:
        chunks.append("**Clarification (structured)**\n" + clar_block)
    tgt_block = _target_output_pack_markdown(payload)
    if tgt_block:
        chunks.append("**Target & Output Pack (structured)**\n" + tgt_block)
    am_block = _autonomy_mutation_markdown(payload)
    if am_block:
        chunks.append("**Autonomy & Mutation (structured)**\n" + am_block)
    sc_block = _scope_selection_markdown(payload)
    if sc_block:
        chunks.append("**Scope Selection (structured)**\n" + sc_block)
    rp_block = _run_plan_markdown(payload)
    if rp_block:
        chunks.append("**Run Plan (structured)**\n" + rp_block)
    sn = payload.get("stepNotes")
    if isinstance(sn, dict):
        for k in sorted(sn.keys(), key=lambda x: int(x) if str(x).isdigit() else 0):
            if _step_note_redundant_with_structured(str(k), payload):
                continue
            v = sn.get(k)
            if isinstance(v, str) and v.strip():
                chunks.append(f"**Step {k}** ({_step_title(k)})\n{v.strip()}")
    extra = payload.get("foundation_brief_raw")
    if isinstance(extra, str) and extra.strip():
        chunks.append(extra.strip())
    return "\n\n".join(chunks).strip()


def _step_title(k: str) -> str:
    titles = (
        "Mission",
        "Contribution Setup",
        "Context Intake",
        "Understanding",
        "Clarification",
        "Target & Output Pack",
        "Autonomy & Mutation",
        "Scope Selection",
        "Run Plan",
        "Review & Generate",
        "Recheck / Repair",
        "Experimental Build",
    )
    try:
        i = int(k)
        if 0 <= i < len(titles):
            return titles[i]
    except ValueError:
        pass
    return k


def refine_foundation_brief(
    workspace_root: Path,
    session_id: str,
    body: dict[str, Any],
) -> dict[str, Any]:
    """
    Load session, build prompt from payload step notes, call llm_chat, merge result into
    payload.foundation_brief and persist.
    """
    if not validate_session_id(session_id):
        return {"ok": False, "error": "invalid_session_id"}
    doc = load_session(workspace_root, session_id)
    if doc is None:
        return {"ok": False, "error": "not_found"}

    provider = str(body.get("provider", "")).strip().lower()
    model_raw = body.get("model")
    model_override: str | None
    if model_raw is None:
        model_override = None
    else:
        ms = str(model_raw).strip()
        model_override = ms if ms else None
    refine = bool(body.get("refine"))

    notes = _notes_markdown(doc.payload)
    if not notes:
        return {
            "ok": False,
            "error": "missing_notes",
            "detail": "Add notes on wizard steps before refining.",
        }

    user_message = _REFINE_INSTRUCTIONS + notes

    from lenses import llm_chat

    llm_out = llm_chat.chat(
        provider,
        user_message,
        model_override,
        workspace_root=workspace_root,
        refine=refine,
        studio_task_id="plans_generation",
    )
    if not llm_out.get("ok"):
        return llm_out

    text = str(llm_out.get("text", "")).strip()
    if not text:
        return {"ok": False, "error": "empty_model_output"}

    from lenses.blueprints_wizard.wizard_domain_normalize import (
        normalize_foundation_brief,
        normalize_wizard_domain,
    )

    merged_payload = dict(doc.payload)
    merged_payload["foundation_brief"] = text
    wd_raw = merged_payload.get("wizard_domain")
    wd = normalize_wizard_domain(wd_raw if isinstance(wd_raw, dict) else {})
    fb_raw = wd.get("foundation_brief")
    fb = normalize_foundation_brief(fb_raw if isinstance(fb_raw, dict) else {})
    fb["markdown"] = text
    fs = dict(fb.get("field_statuses") or {})
    fs.setdefault("llm_foundation_brief", "inferred")
    fb["field_statuses"] = fs
    wd["foundation_brief"] = fb
    merged_payload["wizard_domain"] = normalize_wizard_domain(wd)
    merged = WizardSessionDocument(
        version=doc.version,
        updated_at=doc.updated_at,
        step_index=doc.step_index,
        payload=merged_payload,
    )
    ok_save, err_save = save_session_replace(workspace_root, session_id, merged.to_dict())
    if not ok_save:
        return {"ok": False, "error": err_save or "save_failed", "text": text}

    out: dict[str, Any] = {
        "ok": True,
        "text": text,
        "session": merged.to_dict(),
    }
    if llm_out.get("model"):
        out["model"] = llm_out.get("model")
    if llm_out.get("usage"):
        out["usage"] = llm_out.get("usage")
    if llm_out.get("routing"):
        out["routing"] = llm_out.get("routing")
    return out
