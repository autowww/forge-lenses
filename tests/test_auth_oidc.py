"""OIDC helpers for HTTPS stickerboard guests."""

from __future__ import annotations

from pathlib import Path

import pytest

from lenses.auth_oidc import (
    bootstrap_oidc_env_from_workspace,
    client_may_use_oidc_auth,
    default_oidc_redirect_path,
    load_oidc_config,
    public_request_origin,
)


def test_public_request_origin_env_override(monkeypatch):
    monkeypatch.setenv("LENSES_PUBLIC_ORIGIN", "https://leo.forgedc.net")
    assert (
        public_request_origin(
            host_header="127.0.0.1:8080",
            forwarded_proto="http",
        )
        == "https://leo.forgedc.net"
    )


def test_public_request_origin_forwarded_headers(monkeypatch):
    monkeypatch.delenv("LENSES_PUBLIC_ORIGIN", raising=False)
    assert (
        public_request_origin(
            host_header="127.0.0.1:8080",
            forwarded_proto="https",
            forwarded_host="leo.forgedc.net",
        )
        == "https://leo.forgedc.net"
    )


def test_client_may_use_oidc_auth_when_configured(monkeypatch):
    monkeypatch.setenv("LENSES_OIDC_ISSUER", "https://accounts.google.com")
    monkeypatch.setenv("LENSES_OIDC_CLIENT_ID", "test-client")
    assert client_may_use_oidc_auth("203.0.113.50") is True


def test_default_oidc_redirect_path_stickerboard_base(monkeypatch):
    monkeypatch.delenv("LENSES_OIDC_REDIRECT_PATH", raising=False)
    monkeypatch.setenv(
        "LENSES_STICKERBOARD_PUBLIC_BASE", "https://leo.forgedc.net/stickerboard"
    )
    assert default_oidc_redirect_path() == "/stickerboard/api/auth/oidc/callback"


def test_default_oidc_redirect_path_explicit_override(monkeypatch):
    monkeypatch.setenv("LENSES_OIDC_REDIRECT_PATH", "/api/auth/oidc/callback")
    monkeypatch.setenv(
        "LENSES_STICKERBOARD_PUBLIC_BASE", "https://leo.forgedc.net/stickerboard"
    )
    assert default_oidc_redirect_path() == "/api/auth/oidc/callback"


def test_bootstrap_oidc_env_from_workspace(tmp_path: Path, monkeypatch):
    monkeypatch.delenv("LENSES_OIDC_CLIENT_ID", raising=False)
    local = tmp_path / ".lenses-local"
    local.mkdir()
    (local / "lenses-oidc.env").write_text(
        'LENSES_OIDC_ISSUER=https://accounts.google.com\n'
        'LENSES_OIDC_CLIENT_ID=file-client\n',
        encoding="utf-8",
    )
    bootstrap_oidc_env_from_workspace(tmp_path)
    assert load_oidc_config() is not None
    assert load_oidc_config().client_id == "file-client"
