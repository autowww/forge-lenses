"""Tests for lenses.llm_chat (no network)."""

from __future__ import annotations

import pytest

from lenses import llm_chat
from lenses import llm_completions


def test_providers_available_keys() -> None:
    p = llm_chat.providers_available()
    assert set(p.keys()) == {
        "anthropic",
        "openai",
        "gemini",
        "ollama",
        "openai_compatible",
    }
    assert isinstance(p["ollama"], bool)


def test_chat_invalid_provider() -> None:
    r = llm_chat.chat("unknown", "hi")
    assert r["ok"] is False
    assert r.get("error") == "invalid_provider"


def test_chat_empty_message() -> None:
    r = llm_chat.chat("anthropic", "   ")
    assert r["ok"] is False
    assert r.get("error") == "missing_message"


def test_chat_too_long() -> None:
    r = llm_chat.chat("openai", "x" * (llm_chat.MAX_MESSAGE_CHARS + 1))
    assert r["ok"] is False
    assert r.get("error") == "message_too_long"


def test_chat_not_configured_anthropic(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    r = llm_chat.chat("anthropic", "hello")
    assert r["ok"] is False
    assert r.get("error") == "llm_not_configured"


def test_chat_not_configured_ollama_without_base_url(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("OLLAMA_BASE_URL", raising=False)
    r = llm_chat.chat("ollama", "hello")
    assert r["ok"] is False
    assert r.get("error") == "llm_not_configured"
    assert r.get("detail") == "OLLAMA_BASE_URL"


def test_ollama_daemon_status_without_base_url(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("OLLAMA_BASE_URL", raising=False)
    r = llm_chat.ollama_daemon_status()
    assert r["reachable"] is False
    assert r.get("base") == ""
    assert r.get("configured") is False
    assert r.get("models") == []


def test_providers_reflect_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("LENSES_OPENAI_COMPAT_BASE_URL", raising=False)
    monkeypatch.delenv("OLLAMA_BASE_URL", raising=False)
    p = llm_chat.providers_available()
    assert p["anthropic"] is False
    assert p["openai"] is False
    assert p["gemini"] is False
    assert p["openai_compatible"] is False
    assert p["ollama"] is False

    monkeypatch.setenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434")
    assert llm_chat.providers_available()["ollama"] is True

    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
    p2 = llm_chat.providers_available()
    assert p2["anthropic"] is True


def test_ollama_daemon_status_unreachable(monkeypatch: pytest.MonkeyPatch) -> None:
    def boom(*_a, **_k):
        raise ConnectionRefusedError()

    monkeypatch.setattr(llm_completions.urllib.request, "urlopen", boom)
    monkeypatch.setenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434")
    r = llm_chat.ollama_daemon_status()
    assert r["reachable"] is False
    assert "11434" in r["base"]
    assert r.get("configured") is True


def test_ollama_daemon_status_reachable(monkeypatch: pytest.MonkeyPatch) -> None:
    class FakeResp:
        status = 200

        def read(self) -> bytes:
            return b'{"models":[{"name":"llama3.2"}]}'

        def __enter__(self):
            return self

        def __exit__(self, *_a):
            return None

    def ok(*_a, **_k):
        return FakeResp()

    monkeypatch.setattr(llm_completions.urllib.request, "urlopen", ok)
    monkeypatch.setenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434")
    r = llm_chat.ollama_daemon_status()
    assert r["reachable"] is True
    assert r.get("configured") is True
    assert r.get("models") == ["llama3.2"]


def test_ollama_connection_refused_includes_hint(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_post(url: str, payload: dict, headers: dict | None) -> dict:
        return {"_transport_error": "<urlopen error [Errno 111] Connection refused>"}

    monkeypatch.setattr(llm_completions, "http_post_json_plain", fake_post)
    monkeypatch.setenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434")
    r = llm_chat.chat("ollama", "hello")
    assert r["ok"] is False
    assert r.get("error") == "llm_transport"
    assert "Ollama not listening" in str(r.get("detail", ""))
    assert "11434" in str(r.get("detail", ""))
