"""LLM-backed interpretation using existing ``lenses.llm_chat`` transport."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from lenses.blueprints_wizard.interpretation_normalize import (
    extract_json_object_from_model_text,
    normalize_interpretation_payload,
)
from lenses.blueprints_wizard.refine import _notes_markdown

# Leave headroom under llm_chat.MAX_MESSAGE_CHARS (32_000).
_MAX_NOTES_CHARS = 28_000

_JSON_INSTRUCTIONS = """You are an interpreter for the Forge Blueprints Wizard. Read the wizard notes and produce ONE JSON object only (no markdown outside the JSON). Keys and types:

- "what_user_said": string — concise restatement of what the user communicated (from notes).
- "inferred": array of objects, each: {"id": string (unique), "text": string, "status": one of explicit|inferred|needs_confirmation|unknown, "confidence": optional number between 0 and 1}.
- "needs_confirmation": same shape as "inferred"; items that require user confirmation.
- "unknowns": array of strings — missing context or open gaps not yet in needs_confirmation.
- "foundation_brief_draft": object with EXACTLY these string keys, each mapping to {"text": string, "status": same enum as above, "confidence": optional 0..1}:
  "problem_statement", "desired_outcome", "target_users_stakeholders", "scope", "non_goals",
  "success_metrics", "constraints", "assumptions", "dependencies", "risks", "open_questions", "glossary_key_terms".

Use "unknown" status when you cannot ground a field. Prefer "needs_confirmation" when a guess should be verified. Do not invent compliance or budget facts.

--- Wizard notes ---

"""


def _cap_notes(notes: str) -> str:
    n = (notes or "").strip()
    if len(n) <= _MAX_NOTES_CHARS:
        return n
    return n[:_MAX_NOTES_CHARS] + "\n\n[truncated]"


def run_interpret_llm(
    *,
    workspace_root: Path,
    session_payload: dict[str, Any],
    provider: str,
    model_override: str | None,
    refine: bool,
) -> dict[str, Any]:
    """Call configured LLM; return ``{ok, interpretation}`` or ``{ok: False, error, detail?}``."""
    notes = _notes_markdown(session_payload)
    notes = _cap_notes(notes)
    if not notes.strip():
        return {
            "ok": False,
            "error": "missing_notes",
            "detail": "Add mission, context, or step notes before running interpretation.",
        }

    user_message = _JSON_INSTRUCTIONS + notes

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

    parsed = extract_json_object_from_model_text(text)
    if parsed is None:
        return {
            "ok": False,
            "error": "interpretation_parse_error",
            "detail": "Model did not return valid JSON.",
        }

    interpretation = normalize_interpretation_payload(parsed)
    out: dict[str, Any] = {"ok": True, "interpretation": interpretation}
    if llm_out.get("model"):
        out["model"] = llm_out.get("model")
    if llm_out.get("usage"):
        out["usage"] = llm_out.get("usage")
    if llm_out.get("routing"):
        out["routing"] = llm_out.get("routing")
    return out
