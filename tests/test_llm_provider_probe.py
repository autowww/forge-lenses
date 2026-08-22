"""Tests for lenses.llm_provider_probe."""

from __future__ import annotations

from pathlib import Path

import pytest

from lenses.llm_provider_probe import discover_models, health_ping


def test_discover_openai_not_configured(tmp_path: Path) -> None:
    root = tmp_path / "ws"
    root.mkdir()
    out = discover_models(root, "openai")
    assert out["ok"] is False
    assert out.get("error") == "not_configured"


def test_discover_unknown_provider(tmp_path: Path) -> None:
    root = tmp_path / "ws"
    root.mkdir()
    out = discover_models(root, "azure")
    assert out["ok"] is False
    assert out.get("error") == "unknown_provider"


def test_discover_openai_compatible_probe_base_url(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    root = tmp_path / "ws"
    root.mkdir()
    seen: dict[str, str] = {}

    def fake_http(url: str, hdrs: dict) -> dict:  # type: ignore[type-arg]
        seen["url"] = url
        seen["auth"] = hdrs.get("Authorization", "")
        return {"data": [{"id": "from-probe"}]}

    import lenses.llm_provider_probe as lpp

    monkeypatch.setattr(lpp, "http_get_json", fake_http)
    monkeypatch.setattr(lpp.llm_settings_store, "load_raw", lambda _r: {"keys": {}})
    monkeypatch.setattr(lpp, "merged_openai_compat_base_url", lambda _raw: "")
    out = discover_models(
        root,
        "openai_compatible",
        compat_base_probe="https://granite.example",
        compat_bearer_probe="secret",
    )
    assert out.get("ok") is True
    assert "from-probe" in (out.get("models") or [])
    assert seen["url"] == "https://granite.example/v1/models"
    assert seen["auth"] == "Bearer secret"


def test_health_ping_delegates(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    root = tmp_path / "ws"
    root.mkdir()

    def fake_discover(_wr: Path | None, _p: str, **_kw: object) -> dict:
        return {"ok": True, "models": ["a", "b"]}

    import lenses.llm_provider_probe as lpp

    monkeypatch.setattr(lpp, "discover_models", fake_discover)
    h = health_ping(root, "openai")
    assert h.get("healthy") is True
    assert h.get("model_count") == 2
