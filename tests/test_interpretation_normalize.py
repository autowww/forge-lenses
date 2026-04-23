"""Tests for interpretation payload normalization and JSON extraction."""

from __future__ import annotations

import pytest

from lenses.blueprints_wizard.interpretation_normalize import (
    FOUNDATION_BRIEF_DRAFT_KEYS,
    extract_json_object_from_model_text,
    normalize_interpretation_payload,
)


def test_normalize_empty() -> None:
    out = normalize_interpretation_payload({})
    assert out["schema_version"] == 1
    assert out["what_user_said"] == ""
    assert out["inferred"] == []
    assert out["needs_confirmation"] == []
    assert out["unknowns"] == []
    assert set(out["foundation_brief_draft"].keys()) == set(FOUNDATION_BRIEF_DRAFT_KEYS)
    for k in FOUNDATION_BRIEF_DRAFT_KEYS:
        assert out["foundation_brief_draft"][k]["text"] == ""
        assert out["foundation_brief_draft"][k]["status"] == "unknown"


def test_normalize_coerces_status_and_confidence() -> None:
    raw = {
        "what_user_said": "  hello  ",
        "inferred": [
            {"id": "a1", "text": "t1", "status": "bogus", "confidence": 1.5},
        ],
        "needs_confirmation": [{"id": "b1", "text": "t2", "status": "needs_confirmation"}],
        "unknowns": ["u1", ""],
        "foundation_brief_draft": {
            "problem_statement": {"text": "p", "status": "explicit", "confidence": -0.5},
        },
    }
    out = normalize_interpretation_payload(raw)
    assert out["what_user_said"] == "hello"
    assert out["inferred"][0]["status"] == "unknown"
    assert out["inferred"][0]["confidence"] == 1.0
    assert out["needs_confirmation"][0]["status"] == "needs_confirmation"
    assert out["unknowns"] == ["u1"]
    assert out["foundation_brief_draft"]["problem_statement"]["confidence"] == 0.0


def test_normalize_drops_blocks_without_id() -> None:
    out = normalize_interpretation_payload(
        {"inferred": [{"text": "no id"}, {"id": "x", "text": "ok"}]}
    )
    assert len(out["inferred"]) == 1
    assert out["inferred"][0]["id"] == "x"


def test_extract_json_nested() -> None:
    text = """Here is the result:
```json
{"what_user_said": "x", "inferred": [], "needs_confirmation": [], "unknowns": [], "foundation_brief_draft": {}}
```
"""
    o = extract_json_object_from_model_text(text)
    assert o is not None
    assert o.get("what_user_said") == "x"


def test_extract_json_brace_balanced() -> None:
    text = 'Prefix {"a": {"b": 1}, "c": []} trailing'
    o = extract_json_object_from_model_text(text)
    assert o == {"a": {"b": 1}, "c": []}


def test_extract_json_invalid() -> None:
    assert extract_json_object_from_model_text("") is None
    assert extract_json_object_from_model_text("not json") is None
