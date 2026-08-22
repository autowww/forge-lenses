"""Tests for task-based provider routing (``effective_provider_for_task``)."""

from __future__ import annotations

from pathlib import Path

import pytest

from lenses.llm_resolve import build_routing_preview, effective_provider_for_task, merge_routing_preview_overlay
from lenses.llm_settings_store import load_raw, save_raw


def test_effective_provider_empty_task_id() -> None:
    raw = {"provider": "gemini", "task_routes": {"chat_assistant": {"provider": "openai", "model": ""}}}
    p, mo, _w = effective_provider_for_task(raw, None, "anthropic", None)
    assert p == "anthropic"
    assert mo is None


def test_effective_provider_override() -> None:
    raw = {
        "provider": "gemini",
        "task_routes": {"chat_assistant": {"provider": "openai", "model": "gpt-4o"}},
    }
    p, mo, _w = effective_provider_for_task(raw, "chat_assistant", "gemini", None)
    assert p == "openai"
    assert mo == "gpt-4o"


def test_effective_provider_model_stack_first_only() -> None:
    raw = {
        "provider": "openai",
        "task_routes": {
            "chat_assistant": {
                "provider": "openai",
                "model": "",
                "model_stack": ["gpt-4o", "gpt-4o-mini"],
            }
        },
    }
    p, mo, _w = effective_provider_for_task(raw, "chat_assistant", "openai", None)
    assert p == "openai"
    assert mo == "gpt-4o"


def test_effective_provider_single_mode_model_without_provider_pin() -> None:
    raw = {
        "provider": "openai",
        "routing_mode": "single",
        "task_routes": {"chat_assistant": {"provider": "", "model": "gpt-4o", "model_stack": ["gpt-4o"]}},
    }
    p, mo, _w = effective_provider_for_task(raw, "chat_assistant", "openai", None)
    assert p == "openai"
    assert mo == "gpt-4o"


def test_effective_provider_inherits_model_override() -> None:
    raw = {"provider": "openai", "task_routes": {"chat_assistant": {"provider": "openai", "model": ""}}}
    p, mo, _w = effective_provider_for_task(raw, "chat_assistant", "gemini", "override-model")
    assert p == "openai"
    assert mo == "override-model"


def test_local_only_prefers_ollama_when_configured(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-openai-xxxxxxxxxxxx")
    monkeypatch.setenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434")
    root = tmp_path / "ws"
    root.mkdir()
    raw = load_raw(root)
    raw["routing_mode"] = "advanced"
    raw["provider"] = "openai"
    raw["task_routes"] = {
        "chat_assistant": {
            "provider": "openai",
            "model": "gpt-4o-mini",
            "fallback_provider": "",
            "fallback_model": "",
            "privacy": "local_only",
        }
    }
    save_raw(root, raw)
    p, mo, _w = effective_provider_for_task(raw, "chat_assistant", "openai", None, workspace_root=root)
    assert p == "ollama"


def test_merge_overlay_changes_smart_preview_tier(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-openai-xxxxxxxxxxxx")
    monkeypatch.setenv("GEMINI_API_KEY", "g-test-gemini-xxxxxxxxxxxx")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test-xxxxxxxxxxxx")
    root = tmp_path / "ws2"
    root.mkdir()
    raw = load_raw(root)
    raw["routing_mode"] = "smart"
    raw["tier"] = "MED"
    raw["provider"] = "openai"
    raw["advanced_ui"] = True
    raw["auto_model"] = True
    save_raw(root, raw)
    low = build_routing_preview(root, overlay={"tier": "EXTRA_LOW"})
    high = build_routing_preview(root, overlay={"tier": "TOP"})
    chat_low = next(r for r in low["rows"] if r["task_id"] == "chat_assistant")
    chat_high = next(r for r in high["rows"] if r["task_id"] == "chat_assistant")
    assert chat_low["provider"] == "gemini"
    assert chat_high["provider"] == "anthropic"
    assert low["routing_mode"] == "smart"
    base = load_raw(root)
    merged = merge_routing_preview_overlay(base, {"tier": "TOP"})
    assert merged["tier"] == "TOP"
