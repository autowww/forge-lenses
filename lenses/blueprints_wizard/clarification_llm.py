"""Optional LLM-assisted clarification question suggestions (experimental Blueprints Wizard)."""

from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any

from lenses.blueprints_wizard.session_store import load_session, validate_session_id
from lenses.llm_chat import chat


def clarification_suggest_mock_enabled() -> bool:
    raw = (os.environ.get("LENSES_CLARIFICATION_SUGGEST_MOCK") or "").strip().lower()
    return raw in ("1", "true", "yes", "on")


def _cap_questions(raw: list[dict[str, Any]], max_n: int = 7) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    seen: set[str] = set()
    for item in raw[: max_n * 2]:
        if not isinstance(item, dict):
            continue
        tid = str(item.get("id", "")).strip()
        text = str(item.get("text", "")).strip()
        key = tid or text.lower()[:200]
        if not text or key in seen:
            continue
        seen.add(key)
        out.append(item)
        if len(out) >= max_n:
            break
    return out


def _merge_deterministic_and_extra(
    deterministic: list[dict[str, Any]],
    extra: list[dict[str, Any]],
    max_n: int = 7,
) -> list[dict[str, Any]]:
    merged = list(deterministic) + list(extra)
    return _cap_questions(merged, max_n)


def _mock_extra_questions() -> list[dict[str, Any]]:
    return [
        {
            "id": "llm_mock_1",
            "text": "(LLM mock) What environment constraints matter for rollout?",
            "why_it_matters": "Environment assumptions change verification and release steps.",
            "answer_type": "short_text",
            "default_assumption_if_skipped": "Assume production-like staging exists for final checks.",
            "priority": 25,
        }
    ]


def _extract_json_array(text: str) -> list[dict[str, Any]] | None:
    t = (text or "").strip()
    if not t:
        return None
    try:
        data = json.loads(t)
        if isinstance(data, list):
            return [x for x in data if isinstance(x, dict)]
    except json.JSONDecodeError:
        pass
    m = re.search(r"\[[\s\S]*\]", t)
    if m:
        try:
            data = json.loads(m.group(0))
            if isinstance(data, list):
                return [x for x in data if isinstance(x, dict)]
        except json.JSONDecodeError:
            return None
    return None


def suggest_clarification_questions(
    workspace_root: Path,
    session_id: str,
    body: dict[str, Any],
) -> dict[str, Any]:
    """
    Merge client-built deterministic questions with optional LLM extras.

    Body:
      - ``deterministic_questions``: list of question dicts (JSON-shaped).
      - ``use_llm``: bool — when false, returns capped deterministic list only.
      - ``provider``, optional ``model`` — when ``use_llm`` true.
    """
    if not validate_session_id(session_id):
        return {"ok": False, "error": "invalid_session_id"}

    det_raw = body.get("deterministic_questions")
    deterministic: list[dict[str, Any]] = []
    if isinstance(det_raw, list):
        deterministic = [x for x in det_raw if isinstance(x, dict)]

    use_llm = bool(body.get("use_llm"))
    if not use_llm:
        return {"ok": True, "questions": _cap_questions(deterministic, 7)}

    if clarification_suggest_mock_enabled():
        return {"ok": True, "questions": _merge_deterministic_and_extra(deterministic, _mock_extra_questions())}

    doc = load_session(workspace_root, session_id)
    if doc is None:
        return {"ok": False, "error": "not_found"}

    provider = str(body.get("provider", "")).strip().lower()
    if not provider:
        return {"ok": False, "error": "invalid_provider", "detail": "(empty)"}

    pl = doc.payload
    title = str(pl.get("title", ""))[:500]
    purpose = str(pl.get("purpose", ""))[:2000]
    wd = pl.get("wizard_domain")
    fb_excerpt = ""
    if isinstance(wd, dict):
        fb = wd.get("foundation_brief")
        if isinstance(fb, dict):
            fb_excerpt = str(fb.get("markdown", ""))[:4000]

    det_json = json.dumps(deterministic, ensure_ascii=False)[:12_000]
    message = (
        "You help prioritize clarification questions for a software planning wizard.\n"
        f"Session title: {title}\n"
        f"Purpose: {purpose}\n"
        f"Foundation Brief excerpt:\n{fb_excerpt}\n\n"
        "The client already selected these deterministic questions (JSON):\n"
        f"{det_json}\n\n"
        "Return ONLY a JSON array (no markdown fences) of 0 to 3 NEW question objects that do not "
        "duplicate the deterministic list. Each object must have keys: "
        'id (string), text, why_it_matters, answer_type (short_text|long_text|yes_no|single_choice), '
        "default_assumption_if_skipped (string), priority (number). "
        "Keep text fields concise."
    )

    model_raw = body.get("model")
    model_override = str(model_raw).strip() if model_raw is not None else None
    if model_override == "":
        model_override = None

    out_chat = chat(
        provider,
        message,
        model_override,
        workspace_root=workspace_root,
        refine=bool(body.get("refine")),
        studio_task_id="extraction_classification",
    )
    if not out_chat.get("ok"):
        return out_chat

    text = str(out_chat.get("text", "") or "")
    extra = _extract_json_array(text)
    if extra is None:
        return {"ok": False, "error": "clarification_parse_error", "detail": text[:500]}

    merged = _merge_deterministic_and_extra(deterministic, extra)
    result: dict[str, Any] = {"ok": True, "questions": merged}
    for k in ("model", "usage", "routing"):
        if k in out_chat:
            result[k] = out_chat[k]
    return result
