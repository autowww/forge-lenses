"""Normalize ``payload.interpretation`` (Blueprint Wizard experimental, v1). Pure dict in/out."""

from __future__ import annotations

import json
import re
from typing import Any

from lenses.blueprints_wizard.domain_enums import coerce_interpretation_field_status

INTERPRETATION_SCHEMA_VERSION = 1

# Per-field and block text limits (defense in depth with LLM output).
MAX_WHAT_USER_SAID = 32_000
MAX_BLOCK_TEXT = 16_000
MAX_BLOCK_ID = 256
MAX_UNKNOWN_ITEM = 8_000
MAX_FOUNDATION_SECTION = 24_000
MAX_UNKNOWNS = 64

FOUNDATION_BRIEF_DRAFT_KEYS: tuple[str, ...] = (
    "problem_statement",
    "desired_outcome",
    "target_users_stakeholders",
    "scope",
    "non_goals",
    "success_metrics",
    "constraints",
    "assumptions",
    "dependencies",
    "risks",
    "open_questions",
    "glossary_key_terms",
)


def _coerce_str(v: Any) -> str:
    if v is None:
        return ""
    return str(v).strip()


def _clamp_confidence(v: Any) -> float | None:
    if v is None:
        return None
    try:
        x = float(v)
    except (TypeError, ValueError):
        return None
    if x != x:  # NaN
        return None
    return max(0.0, min(1.0, x))


def normalize_interpretation_block(raw: Any) -> dict[str, Any] | None:
    if not isinstance(raw, dict):
        return None
    bid = _coerce_str(raw.get("id"))[:MAX_BLOCK_ID]
    if not bid:
        return None
    text = _coerce_str(raw.get("text"))[:MAX_BLOCK_TEXT]
    status = coerce_interpretation_field_status(raw.get("status"))
    conf = _clamp_confidence(raw.get("confidence"))
    out: dict[str, Any] = {"id": bid, "text": text, "status": status}
    if conf is not None:
        out["confidence"] = conf
    return out


def normalize_interpretation_blocks(raw: Any) -> list[dict[str, Any]]:
    if not isinstance(raw, list):
        return []
    out: list[dict[str, Any]] = []
    for item in raw[:256]:
        b = normalize_interpretation_block(item)
        if b is not None:
            out.append(b)
    return out


def normalize_unknowns_list(raw: Any) -> list[str]:
    if not isinstance(raw, list):
        return []
    out: list[str] = []
    for item in raw[:MAX_UNKNOWNS]:
        s = _coerce_str(item)[:MAX_UNKNOWN_ITEM]
        if s:
            out.append(s)
    return out


def normalize_foundation_brief_draft_section(raw: Any) -> dict[str, Any]:
    defaults = {"text": "", "status": "unknown"}
    if not isinstance(raw, dict):
        return dict(defaults)
    text = _coerce_str(raw.get("text"))[:MAX_FOUNDATION_SECTION]
    status = coerce_interpretation_field_status(raw.get("status"))
    out: dict[str, Any] = {"text": text, "status": status}
    conf = _clamp_confidence(raw.get("confidence"))
    if conf is not None:
        out["confidence"] = conf
    return out


def normalize_foundation_brief_draft(raw: Any) -> dict[str, Any]:
    out: dict[str, Any] = {}
    if not isinstance(raw, dict):
        raw = {}
    for key in FOUNDATION_BRIEF_DRAFT_KEYS:
        out[key] = normalize_foundation_brief_draft_section(raw.get(key))
    return out


def normalize_interpretation_payload(raw: Any) -> dict[str, Any]:
    """Full v1 interpretation document for ``payload.interpretation``."""
    defaults: dict[str, Any] = {
        "schema_version": INTERPRETATION_SCHEMA_VERSION,
        "what_user_said": "",
        "inferred": [],
        "needs_confirmation": [],
        "unknowns": [],
        "foundation_brief_draft": normalize_foundation_brief_draft({}),
    }
    if not isinstance(raw, dict):
        return dict(defaults)

    sv = raw.get("schema_version")
    if isinstance(sv, int) and not isinstance(sv, bool):
        schema_version = max(1, min(99, sv))
    elif isinstance(sv, str) and sv.isdigit():
        schema_version = max(1, min(99, int(sv)))
    else:
        schema_version = INTERPRETATION_SCHEMA_VERSION

    out = dict(defaults)
    out["schema_version"] = schema_version
    out["what_user_said"] = _coerce_str(raw.get("what_user_said"))[:MAX_WHAT_USER_SAID]
    out["inferred"] = normalize_interpretation_blocks(raw.get("inferred"))
    out["needs_confirmation"] = normalize_interpretation_blocks(raw.get("needs_confirmation"))
    out["unknowns"] = normalize_unknowns_list(raw.get("unknowns"))
    out["foundation_brief_draft"] = normalize_foundation_brief_draft(raw.get("foundation_brief_draft"))
    ua = raw.get("updated_at")
    if isinstance(ua, str) and ua.strip():
        out["updated_at"] = _coerce_str(ua)[:64]
    return out


def extract_json_object_from_model_text(text: str) -> dict[str, Any] | None:
    """
    Parse a JSON object from LLM output (may include markdown fences or prose).
    Prefer brace-balanced extraction for nested structures.
    """
    if not text or not str(text).strip():
        return None
    t = str(text).strip()
    # Strip ```json ... ``` fence if present
    fence = re.search(r"```(?:json)?\s*([\s\S]*?)```", t, re.IGNORECASE)
    if fence:
        t = fence.group(1).strip()

    start = t.find("{")
    if start < 0:
        try:
            o = json.loads(t)
        except json.JSONDecodeError:
            return None
        return o if isinstance(o, dict) else None

    depth = 0
    for i in range(start, len(t)):
        c = t[i]
        if c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                chunk = t[start : i + 1]
                try:
                    o = json.loads(chunk)
                except json.JSONDecodeError:
                    return None
                return o if isinstance(o, dict) else None
    try:
        o = json.loads(t)
    except json.JSONDecodeError:
        return None
    return o if isinstance(o, dict) else None
