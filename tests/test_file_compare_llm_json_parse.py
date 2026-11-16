"""Unit tests for hybrid compare LLM JSON parsing (no network)."""

from __future__ import annotations

import pytest

from lib.file_compare_llm.llm_pipeline import parse_llm_json


def test_parse_llm_json_plain_object() -> None:
    assert parse_llm_json('{"a": 1}') == {"a": 1}


def test_parse_llm_json_fenced() -> None:
    text = """Here you go:
```json
{"ok": true, "n": 2}
```
"""
    assert parse_llm_json(text) == {"ok": True, "n": 2}


def test_parse_llm_json_with_prefix_noise() -> None:
    text = 'Sure. {"x": "y"} trailing'
    assert parse_llm_json(text) == {"x": "y"}


def test_parse_llm_json_invalid_raises() -> None:
    with pytest.raises(ValueError):
        parse_llm_json("not json at all")
