"""Tests for URL-backed LLM catalog snapshot + diff (no live HTTP)."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

from lenses.llm_model_catalog_snapshot import (
    diff_new_models,
    normalize_origin,
    refresh_catalog_notifications,
    snapshot_path,
    source_key,
)


def test_normalize_origin_strips_path_and_trailing_slash() -> None:
    assert normalize_origin("HTTP://127.0.0.1:11434/api/tags") == "http://127.0.0.1:11434"
    assert normalize_origin("https://Example.com:443/foo/") == "https://example.com"


def test_source_key_stable() -> None:
    assert source_key("ollama", "http://127.0.0.1:11434/") == "ollama|http://127.0.0.1:11434"


def test_diff_new_models() -> None:
    assert diff_new_models(["a"], ["a", "b", "c"]) == ["b", "c"]
    assert diff_new_models([], ["x"]) == ["x"]
    assert diff_new_models(["x"], ["x"]) == []


def test_refresh_baseline_then_notify(tmp_path: Path) -> None:
    wr = tmp_path / "ws"
    (wr / ".lenses-local").mkdir(parents=True)

    def fake_probe(_root: Path, provider: str) -> dict:
        if provider == "openai_compatible":
            return {"ok": True, "models": ["m1", "m2"]}
        return {"ok": False, "error": "skip"}

    with patch("lenses.llm_model_catalog_snapshot._url_sources_to_probe", return_value=[("openai_compatible", "http://127.0.0.1:9")]):
        with patch("lenses.llm_model_catalog_snapshot.discover_models", side_effect=fake_probe):
            r1 = refresh_catalog_notifications(wr)
    assert r1["ok"] is True
    assert r1["notifications"] == []
    assert any(c.get("baseline") for c in r1["checked"])

    def fake_probe2(_root: Path, provider: str) -> dict:
        return {"ok": True, "models": ["m1", "m2", "m3"]}

    with patch("lenses.llm_model_catalog_snapshot._url_sources_to_probe", return_value=[("openai_compatible", "http://127.0.0.1:9")]):
        with patch("lenses.llm_model_catalog_snapshot.discover_models", side_effect=fake_probe2):
            r2 = refresh_catalog_notifications(wr)
    assert r2["ok"] is True
    assert len(r2["notifications"]) == 1
    assert r2["notifications"][0]["new_models"] == ["m3"]
    assert "/chat?provider=" in r2["notifications"][0]["try_chat_to"]

    snap = json.loads(snapshot_path(wr).read_text(encoding="utf-8"))
    key = source_key("openai_compatible", "http://127.0.0.1:9")
    assert snap["sources"][key]["model_ids"] == ["m1", "m2", "m3"]


def test_refresh_no_url_sources_skips_io(tmp_path: Path) -> None:
    wr = tmp_path / "ws2"
    with patch("lenses.llm_model_catalog_snapshot._url_sources_to_probe", return_value=[]):
        r = refresh_catalog_notifications(wr)
    assert r == {"ok": True, "notifications": [], "checked": []}
    assert not (wr / ".lenses-local").exists()
