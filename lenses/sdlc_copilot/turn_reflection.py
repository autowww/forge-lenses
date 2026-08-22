"""Post-turn reflection: whether the user question was answered, and suggested follow-ups (heuristic + optional LLM)."""

from __future__ import annotations

import json
import os
import re
from typing import Any

def _effective_citation_count(
    citation_count: int,
    citations: list[dict[str, Any]] | None,
) -> int:
    if citations is not None:
        return len(citations)
    return int(citation_count)


def _citation_kind_diversity(citations: list[dict[str, Any]] | None) -> int:
    if not citations:
        return 0
    kinds: set[str] = set()
    for c in citations:
        if not isinstance(c, dict):
            continue
        k = str(c.get("kind") or "").strip()
        kinds.add(k if k else "__unknown__")
    return len(kinds)


def _grounded_yes_confidence(
    *,
    cc: int,
    citations: list[dict[str, Any]] | None,
    assistant_text: str,
) -> float:
    """Upper bound for satisfaction when the reply appears helpful (citations + shape); not accuracy."""
    cc_n = max(int(cc), 1)
    base = 0.52 + 0.035 * min(cc_n, 12)
    kd = _citation_kind_diversity(citations)
    diversity_adj = 0.01 * min(kd, 6)
    alen = len((assistant_text or "").strip())
    length_adj = 0.006 * min(alen // 400, 8)
    raw = base + diversity_adj + length_adj
    return round(min(0.88, max(0.55, raw)), 2)


# Reply signals the user likely was not helped, even if citations exist (model deflected).
# Includes soft “context gap” wording: polite prose that still means the request was not met.
_DEFLECTS_OR_DECLINES = re.compile(
    r"unable to assist|"
    r"i'?m unable to assist|"
    r"i'?m unable to provide|"
    r"cannot assist with|"
    r"not able to help(?: you)? with|"
    r"none of these (?:items )?(?:pertain|relate)|"
    r"does not pertain|"
    r"do not pertain to|"
    r"apologies for any inconvenience|"
    r"doesn'?t seem to be any information|"
    r"there doesn'?t seem to be any information|"
    r"no information (?:in the provided context|suggesting)|"
    r"unable to provide an answer|"
    r"cannot provide an answer|"
    r"using only the information provided|"
    r"doesn'?t directly address your question|"
    r"implementation-?specific help|"
    r"separate documentation|"
    r"\bmissing_note\b|"
    r"unable to provide.*(?:answer|information)|"
    r"i cannot help you (?:with|add)|"
    # Context does not support answering the user's yes/no or how (often still has citations).
    r"(?:the |)(?:provided |)context\s+(?:does not|doesn'?t|do not|don'?t)\s+"
    r"(?:contain|include|cover)\s+(?:any\s+)?(?:information|details?)\s+about\s+(?:whether|if|how)\b|"
    r"(?:the |)(?:provided |)context\s+(?:does not|doesn'?t)\s+"
    r"(?:indicate|show|state|establish)\s+(?:whether|if|how)\b|"
    r"does not contain information about (?:whether|if|how)|"
    r"doesn'?t contain information about (?:whether|if|how)|"
    r"(?:cannot|can'?t)\s+(?:tell|say|determine)\s+(?:you\s+)?(?:whether|if|how)\b.*\b(?:context|sources?)\b|"
    r"(?:cannot|can'?t)\s+(?:answer|determine)\s+(?:that|this|whether|if)\b.*\b(?:context|sources?)\b|"
    r"not\s+(?:possible|clear)\s+to\s+(?:answer|determine)\s+.*\b(?:from|with|using)\b.*\b(?:context|sources?)\b|"
    r"no\s+(?:specific\s+)?(?:information|documentation|details?)\s+(?:in|from)\s+(?:the\s+)?(?:provided\s+)?context|"
    r"(?:i|we)\s+(?:do\s+not|don'?t)\s+have\s+(?:specific\s+)?(?:information|details?)\s+"
    r"(?:in|from)\s+(?:the\s+)?(?:provided\s+)?context",
    re.IGNORECASE,
)


def reply_deflects_despite_sources(assistant_text: str) -> bool:
    """True when the assistant text signals refusal / context gap (for multi-step retry)."""
    return _reply_deflects_despite_sources(assistant_text)


def _reply_deflects_despite_sources(assistant_text: str) -> bool:
    t = (assistant_text or "").strip()
    if len(t) < 24:
        return False
    return bool(_DEFLECTS_OR_DECLINES.search(t))


def _satisfaction_unmet_outcome(
    *,
    user_message: str,
    assistant_text: str,
    effective_count: int,
) -> dict[str, Any] | None:
    """If the model declined or said context lacks the answer, treat satisfaction as low (not 'yes')."""
    if effective_count <= 0:
        return None
    if not _reply_deflects_despite_sources(assistant_text):
        return None
    um = (user_message or "").strip().lower()
    # Slightly lower score when the user clearly asked for something concrete.
    concrete = bool(
        re.search(
            r"\b(where|how)\s+(can|do|should)\s+i\b|"
            r"\bcan\s+i\b|\bcould\s+i\b|\bcan\s+we\b|"
            r"let'?s\s+add\b|"
            r"add\s+(some\s+)?\w+|"
            r"suggest\s+where\b|"
            r"sticky\s+notes?\b|"
            r"how\s+do\s+i\s+find\b|"
            r"\bis\s+there\s+(a\s+)?way\b",
            um,
        )
    )
    conf = 0.26 if concrete else 0.34
    return {
        "answered": "partial",
        "confidence": conf,
        "agent_note": (
            "The reply says grounded material does not answer your specific ask (or deflects)—"
            "the score reflects whether your request was met, not how polished the prose is."
        ),
        "suggested_follow_up": (
            "Try another Studio screen where the feature is exposed, widen related markdown in context, "
            "or ask to search the workspace/repo for implementation details."
        ),
        "adjust_context": True,
        "source": "heuristic",
        "confidence_semantic": "satisfaction",
    }


_HEDGE_PATTERNS = re.compile(
    r"(don't|do not) have enough evidence|"
    r"not enough evidence|"
    r"cannot confirm|can't confirm|"
    r"unable to (confirm|determine)|"
    r"unclear from (the|these) sources|"
    r"insufficient (information|evidence|data)|"
    r"i don't know|i do not know|"
    r"no specific reference|"
    r"does not appear in (the|these) sources|"
    r"not (explicitly )?mentioned in (the|these) sources|"
    r"based on (the|these) sources alone|"
    r"need (?:more|additional) (?:details|context|information) (?:to|before)|"
    r"(?:would|could) need (?:more|further|additional) (?:details|context)",
    re.IGNORECASE,
)


def _env_llm_reflection() -> bool:
    v = (os.environ.get("LENSES_COPILOT_LLM_TURN_REFLECTION") or "").strip().lower()
    return v in ("1", "true", "yes", "on")


def _try_llm_reflection_json(
    *,
    workspace_root: Any,
    provider: str,
    model_override: str | None,
    user_message: str,
    assistant_text: str,
    citation_count: int,
) -> dict[str, Any] | None:
    if not _env_llm_reflection():
        return None
    try:
        from lenses import llm_chat
    except OSError:
        return None

    um = (user_message or "").strip()[:1200]
    at = (assistant_text or "").strip()[:4000]
    prompt = (
        "You evaluate whether the USER's concrete request was MET (information or action they needed), "
        "not politeness, grammar, or citation count. "
        "Given USER_QUESTION and ASSISTANT_ANSWER, reply with a single JSON object only (no markdown), keys:\n"
        '{"answered":"yes|partial|no","confidence":0.0-1.0,"agent_note":"<=220 chars",'
        '"suggested_follow_up":"<=180 chars or empty","adjust_context":true|false}\n'
        "confidence: 0.0–0.35 if they got essentially none of what they asked for; "
        "0.4–0.6 if the reply mostly clarifies limits or asks for more detail without answering; "
        "high only if the answer substantively delivers what was asked. "
        "Use low scores when the assistant says context does not say whether/how/if, or only redirects. "
        f"\n\nUSER_QUESTION:\n{um}\n\nASSISTANT_ANSWER:\n{at}\n\n"
        f"CITATION_COUNT: {citation_count}\n"
    )
    r = llm_chat.chat(
        provider,
        prompt,
        model_override,
        workspace_root=workspace_root,
        refine=False,
        studio_task_id="copilot_turn_reflect",
    )
    if not r.get("ok"):
        return None
    raw = str(r.get("text") or "").strip()
    if not raw:
        return None
    if raw.startswith("```"):
        raw = re.sub(r"^```[a-zA-Z0-9]*\s*", "", raw)
        raw = re.sub(r"\s*```$", "", raw).strip()
    try:
        o = json.loads(raw)
    except json.JSONDecodeError:
        return None
    if not isinstance(o, dict):
        return None
    return o


def build_turn_reflection(
    *,
    user_message: str,
    assistant_text: str,
    citation_count: int,
    grounding_truncated: bool,
    workspace_root: Any | None = None,
    provider: str | None = None,
    model_override: str | None = None,
    citations: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Return a small structured object for the Studio UI (and optional LLM override)."""
    effective_count = _effective_citation_count(citation_count, citations)
    text = (assistant_text or "").strip()
    low = text.lower()
    hedged = bool(_HEDGE_PATTERNS.search(text))
    very_short = len(text) < 24

    if hedged or (effective_count <= 0 and very_short):
        answered = "no" if hedged and effective_count <= 0 else "partial"
        if answered == "no":
            confidence = 0.35
        elif hedged and effective_count > 0:
            # Citations present but the model still signals insufficient evidence → request likely unmet.
            confidence = 0.37
        else:
            confidence = 0.5
        parts: list[str] = []
        if effective_count <= 0:
            parts.append("No numbered sources were attached to this reply.")
        if hedged:
            parts.append("The answer hedges or says evidence is insufficient.")
        if grounding_truncated:
            parts.append("Grounding was trimmed for size.")
        agent_note = " ".join(parts) if parts else "The reply may not fully answer the question."
        suggested = (
            "Try widening context: open a project or doc-heavy page, or name a file path."
            if effective_count <= 0
            else "Try a narrower question, or ask what evidence would decide it."
        )
        out: dict[str, Any] = {
            "answered": answered,
            "confidence": confidence,
            "agent_note": agent_note[:400],
            "suggested_follow_up": suggested[:400],
            "adjust_context": effective_count <= 0 or hedged,
            "source": "heuristic",
        }
    elif effective_count <= 0 or grounding_truncated:
        answered = "partial"
        agent_note = (
            "Few or no citations were grounded for this turn."
            if effective_count <= 0
            else "Context was truncated before the model ran."
        )
        out = {
            "answered": answered,
            "confidence": 0.55,
            "agent_note": agent_note,
            "suggested_follow_up": (
                "Add a workspace doc to related context, or navigate to a more specific Studio page."
            ),
            "adjust_context": True,
            "source": "heuristic",
        }
    else:
        gap = _satisfaction_unmet_outcome(
            user_message=user_message,
            assistant_text=text,
            effective_count=effective_count,
        )
        if gap is not None:
            out = gap
        else:
            confidence = _grounded_yes_confidence(
                cc=effective_count,
                citations=citations,
                assistant_text=text,
            )
            out = {
                "answered": "yes",
                "confidence": confidence,
                "agent_note": (
                    "Proxy from evidence mix and answer shape only—high here does not guarantee "
                    "you received every concrete action or fact you asked for."
                ),
                "suggested_follow_up": "",
                "adjust_context": False,
                "source": "heuristic",
                "confidence_semantic": "satisfaction",
            }

    if workspace_root is not None and provider:
        llm = _try_llm_reflection_json(
            workspace_root=workspace_root,
            provider=provider,
            model_override=model_override,
            user_message=user_message,
            assistant_text=assistant_text,
            citation_count=effective_count,
        )
        if isinstance(llm, dict):
            for k in ("answered", "confidence", "agent_note", "suggested_follow_up", "adjust_context"):
                if k in llm and llm[k] is not None:
                    out[k] = llm[k]  # type: ignore[index]
            out["source"] = "llm"
            out["confidence_semantic"] = "satisfaction"
    return out
