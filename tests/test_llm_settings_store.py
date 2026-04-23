"""Tests for lenses.llm_settings_store."""

from __future__ import annotations

from pathlib import Path

import pytest

from lenses.llm_resolve import merged_secret_keys
from lenses.llm_settings_store import (
    load_raw,
    merge_save,
    merged_openai_compat_base_url,
    settings_path,
    sanitize_for_get,
    save_raw,
)


def test_merge_save_first_run_wizard_dismissed(tmp_path: Path) -> None:
    root = tmp_path / "ws"
    root.mkdir()
    save_raw(root, load_raw(root))
    merged = merge_save(root, {"first_run_wizard_dismissed": True})
    save_raw(root, merged)
    data = load_raw(root)
    assert data.get("first_run_wizard_dismissed") is True


def test_merge_save_preserves_empty_key(tmp_path: Path) -> None:
    root = tmp_path / "ws"
    root.mkdir()
    save_raw(root, load_raw(root))
    merged = merge_save(root, {"keys": {"openai": "sk-new"}})
    save_raw(root, merged)
    data = load_raw(root)
    assert data["keys"]["openai"] == "sk-new"
    merged2 = merge_save(root, {"keys": {"openai": ""}})
    save_raw(root, merged2)
    data2 = load_raw(root)
    assert data2["keys"]["openai"] == "sk-new"


def test_sanitize_for_get_reflects_openai_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "sk-env12345678901234")
    data = {
        "keys": {
            "anthropic": "",
            "openai": "",
            "gemini": "",
            "openai_compatible": "",
        }
    }
    out = sanitize_for_get(data)
    o = out["keys"]["openai"]
    assert o["set"] is True
    assert o["from_env"] is True
    assert o["from_file"] is False
    assert o["env_hint"] == "OPENAI_API_KEY"
    assert "sk-e" in o["preview"]


def test_merge_save_task_routes(tmp_path: Path) -> None:
    root = tmp_path / "ws"
    root.mkdir()
    save_raw(root, load_raw(root))
    merged = merge_save(
        root,
        {
            "task_routes": {
                "chat_assistant": {"provider": "openai", "model": "gpt-4o-mini"},
                "search_knowledge": {"provider": "", "model": ""},
            }
        },
    )
    save_raw(root, merged)
    data = load_raw(root)
    assert data["version"] == 2
    assert data["task_routes"]["chat_assistant"]["provider"] == "openai"
    assert data["task_routes"]["chat_assistant"]["model"] == "gpt-4o-mini"
    assert data["task_routes"]["chat_assistant"]["model_stack"] == ["gpt-4o-mini"]


def test_merge_save_task_routes_model_stack(tmp_path: Path) -> None:
    root = tmp_path / "ws2"
    root.mkdir()
    save_raw(root, load_raw(root))
    merged = merge_save(
        root,
        {
            "task_routes": {
                "code_automation": {
                    "provider": "openai",
                    "model": "",
                    "model_stack": ["gpt-4o", "gpt-4o-mini"],
                }
            }
        },
    )
    save_raw(root, merged)
    data = load_raw(root)
    assert data["task_routes"]["code_automation"]["model"] == "gpt-4o"
    assert data["task_routes"]["code_automation"]["model_stack"] == ["gpt-4o", "gpt-4o-mini"]


def test_sanitize_for_get_prefers_file_over_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "sk-from-env-xxxxxxxxxxxx")
    data = {
        "keys": {
            "anthropic": "",
            "openai": "sk-from-file-xxxxxxxxxxxx",
            "gemini": "",
            "openai_compatible": "",
        }
    }
    out = sanitize_for_get(data)
    o = out["keys"]["openai"]
    assert o["set"] is True
    assert o["from_file"] is True
    assert o["from_env"] is True
    assert "sk-f" in o["preview"]


def test_merged_openai_compat_base_url_file_overrides_env(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("LENSES_OPENAI_COMPAT_BASE_URL", "https://env.example/v1")
    raw = {"openai_compatible_base_url": "https://file.example"}
    assert merged_openai_compat_base_url(raw) == "https://file.example"


def test_merged_openai_compat_base_url_env_when_file_empty(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("LENSES_OPENAI_COMPAT_BASE_URL", "https://env.example")
    raw = {"openai_compatible_base_url": ""}
    assert merged_openai_compat_base_url(raw) == "https://env.example"


def test_sanitize_openai_compat_endpoint(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LENSES_OPENAI_COMPAT_BASE_URL", "https://gw.example")
    data = {
        "keys": {
            "anthropic": "",
            "openai": "",
            "gemini": "",
            "openai_compatible": "",
        },
        "openai_compatible_base_url": "",
    }
    out = sanitize_for_get(data)
    ep = out["openai_compatible_endpoint"]
    assert ep["set"] is True
    assert ep["from_env"] is True
    assert ep["from_file"] is False
    assert "gw.example" in ep["preview"]
    assert "openai_compatible_base_url" not in out


def test_merge_save_openai_compat_base_url(tmp_path: Path) -> None:
    root = tmp_path / "ws"
    root.mkdir()
    save_raw(root, load_raw(root))
    merged = merge_save(root, {"openai_compatible_base_url": "https://custom.local"})
    save_raw(root, merged)
    assert load_raw(root)["openai_compatible_base_url"] == "https://custom.local"
    merged2 = merge_save(root, {"openai_compatible_base_url": ""})
    save_raw(root, merged2)
    assert load_raw(root)["openai_compatible_base_url"] == "https://custom.local"


def test_merge_save_ignores_non_string_key_values(tmp_path: Path) -> None:
    root = tmp_path / "ws"
    root.mkdir()
    base = load_raw(root)
    base["keys"]["openai_compatible"] = "sk-compat-secret-xxxxxxxx"
    save_raw(root, base)
    merged = merge_save(
        root,
        {
            "keys": {
                "openai_compatible": {"set": True, "preview": "sk-…xxxx"},
            }
        },
    )
    save_raw(root, merged)
    assert load_raw(root)["keys"]["openai_compatible"] == "sk-compat-secret-xxxxxxxx"


def test_load_raw_repairs_non_string_keys(tmp_path: Path) -> None:
    root = tmp_path / "ws"
    root.mkdir()
    p = settings_path(root)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(
        '{"version": 2, "keys": {"openai_compatible": {"set": true}}, '
        '"openai_compatible_base_url": "https://gw.example"}',
        encoding="utf-8",
    )
    data = load_raw(root)
    assert data["keys"]["openai_compatible"] == ""
    assert data["openai_compatible_base_url"] == "https://gw.example"


def test_merged_secret_keys_ignores_dict_file_shape(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("LENSES_OPENAI_COMPAT_KEY", raising=False)
    keys = merged_secret_keys({"keys": {"openai_compatible": {"set": True, "preview": "x"}}})
    assert keys["openai_compatible"] == ""
