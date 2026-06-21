"""Tests for lenses.llm_completions (provider transport only)."""

from __future__ import annotations

import pytest

from lenses import llm_completions


def test_complete_user_message_invalid_provider() -> None:
    r = llm_completions.complete_user_message("unknown", "hi", None, {})
    assert r["ok"] is False
    assert r.get("error") == "invalid_provider"


def test_complete_openai_not_configured(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    r = llm_completions.complete_user_message("openai", "hello", None, {})
    assert r["ok"] is False
    assert r.get("error") == "llm_not_configured"


def test_openai_compat_chat_timeout_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LENSES_OPENAI_COMPAT_HTTP_TIMEOUT_SEC", "240")
    assert llm_completions._openai_compat_chat_timeout_sec() == 240.0
    monkeypatch.delenv("LENSES_OPENAI_COMPAT_HTTP_TIMEOUT_SEC", raising=False)
    assert llm_completions._openai_compat_chat_timeout_sec() == llm_completions.DEFAULT_LOCAL_CHAT_TIMEOUT_SEC
