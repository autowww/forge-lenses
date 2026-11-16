"""Tests for lenses.ollama_admin HTTP helpers."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from lenses import ollama_admin


def test_ollama_pull_missing_model() -> None:
    assert ollama_admin.ollama_pull("  ") == {"ok": False, "error": "missing_model"}


def test_ollama_delete_not_configured(monkeypatch) -> None:
    monkeypatch.delenv("OLLAMA_BASE_URL", raising=False)
    monkeypatch.setenv("OLLAMA_BASE_URL", "")
    out = ollama_admin.ollama_delete("x")
    assert out["ok"] is False
    assert out.get("error") == "not_configured"


@patch("lenses.ollama_admin.urllib.request.urlopen")
def test_ollama_delete_success(mock_urlopen, monkeypatch) -> None:
    monkeypatch.setenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434")
    resp = MagicMock()
    resp.read.return_value = b"{}"
    resp.__enter__ = MagicMock(return_value=resp)
    resp.__exit__ = MagicMock(return_value=False)
    mock_urlopen.return_value = resp
    out = ollama_admin.ollama_delete("llama3.2:latest")
    assert out["ok"] is True
    assert out.get("result") == {}


@patch("lenses.ollama_admin.urllib.request.urlopen")
def test_ollama_pull_ndjson_stream(mock_urlopen, monkeypatch) -> None:
    monkeypatch.setenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434")
    body = b'{"status":"pulling"}\n{"status":"success"}\n'
    resp = MagicMock()
    resp.read.return_value = body
    resp.__enter__ = MagicMock(return_value=resp)
    resp.__exit__ = MagicMock(return_value=False)
    mock_urlopen.return_value = resp
    out = ollama_admin.ollama_pull("tiny", stream=False)
    assert out["ok"] is True
    assert out.get("result") == {"status": "success"}
