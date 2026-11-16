"""Stickerboard guest share tokens and scope helpers."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from lenses.sticker_board import (
    BOARD_VERSION,
    REGISTRY_VERSION,
    share_add_guest_acl,
    validate_board,
)
from lenses.serve_rbac import LOCAL_LOOPBACK_FACILITATOR_LOGIN, resolve_facilitator_login
from lenses.sticker_board import resolve_board_display_label
from lenses.sticker_board import load_board, local_board_data_path
from lenses.sticker_board_share import (
    build_public_url,
    normalize_stickerboard_api_path,
    share_metadata,
    share_public_config,
    stickerboard_loopback_dev_auth_enabled,
    SHARE_SCOPE_COOKIE,
    is_valid_share_token,
    new_share_token,
    resolve_share_scope,
    share_join,
    share_metadata,
    share_revoke,
    share_scope_allows_path,
    share_start,
    stickerboard_port_allows_path,
)


def _ws(tmp_path: Path) -> Path:
    (tmp_path / ".lenses-local").mkdir(parents=True, exist_ok=True)
    return tmp_path


def test_build_public_url_uses_env_base(monkeypatch):
    monkeypatch.setenv(
        "LENSES_STICKERBOARD_PUBLIC_BASE", "https://leo.forgedc.net/stickerboard"
    )
    url = build_public_url("abcToken123456789012")
    assert url == "https://leo.forgedc.net/stickerboard/#/abcToken123456789012"
    cfg = share_public_config()
    assert cfg["public_base"] == "https://leo.forgedc.net/stickerboard"
    assert cfg["from_env"] is True
    assert cfg["public_base_configured"] is True


def test_loopback_env_not_treated_as_configured(monkeypatch):
    monkeypatch.setenv("LENSES_STICKERBOARD_PUBLIC_BASE", "http://127.0.0.1:9999")
    cfg = share_public_config()
    assert cfg["from_env"] is False
    assert cfg["public_base_configured"] is False


def test_workspace_public_env_overrides_loopback(monkeypatch, tmp_path: Path):
    monkeypatch.setenv("LENSES_STICKERBOARD_PUBLIC_BASE", "http://127.0.0.1:9999")
    local = tmp_path / ".lenses-local"
    local.mkdir()
    (local / "stickerboard-public.env").write_text(
        "LENSES_STICKERBOARD_PUBLIC_BASE=https://leo.forgedc.net/stickerboard\n",
        encoding="utf-8",
    )
    from lenses.sticker_board_share import bootstrap_stickerboard_public_from_workspace

    bootstrap_stickerboard_public_from_workspace(tmp_path)
    cfg = share_public_config(tmp_path)
    assert cfg["public_base"] == "https://leo.forgedc.net/stickerboard"
    assert cfg["public_base_configured"] is True


def test_build_public_url_defaults_to_9999(monkeypatch):
    monkeypatch.delenv("LENSES_STICKERBOARD_PUBLIC_BASE", raising=False)
    monkeypatch.setenv("LENSES_STICKERBOARD_PORT", "9999")
    url = build_public_url("abcToken123456789012")
    assert url == "http://127.0.0.1:9999/#/abcToken123456789012"


def test_build_public_url_main_port_stickerboard_path(monkeypatch):
    monkeypatch.delenv("LENSES_STICKERBOARD_PUBLIC_BASE", raising=False)
    monkeypatch.setenv("LENSES_STICKERBOARD_PORT", "0")
    monkeypatch.setenv("LENSES_PORT", "8080")
    url = build_public_url("tok123456789012345678")
    assert url == "http://127.0.0.1:8080/stickerboard/#/tok123456789012345678"


def test_new_share_token_random():
    a = new_share_token()
    b = new_share_token()
    assert a != b
    assert is_valid_share_token(a)


def test_share_start_revoke_and_join(tmp_path: Path):
    ws = _ws(tmp_path)
    result, err = share_start(
        ws,
        board_id="board123456789012345678",
        guest_role="edit",
        created_by_login="fac@example.com",
    )
    assert err == ""
    assert result
    token = result["share_token"]
    meta, merr = share_metadata(ws, token)
    assert merr == ""
    assert meta and meta["guest_role"] == "edit"

    joined, jerr = share_join(
        ws,
        share_token=token,
        login="guest@example.com",
        display_name="Alex Guest",
    )
    assert jerr == ""
    assert joined
    meta2, _ = share_metadata(ws, token)
    assert meta2
    assert len(meta2.get("participants") or []) == 1

    ok, rerr = share_revoke(ws, share_token=token, actor_login="fac@example.com")
    assert ok and rerr == ""
    meta3, _ = share_metadata(ws, token)
    assert meta3 is None


def test_stickerboard_loopback_dev_auth_env(monkeypatch):
    monkeypatch.delenv("LENSES_STICKERBOARD_LOOPBACK_DEV_AUTH", raising=False)
    assert not stickerboard_loopback_dev_auth_enabled()
    monkeypatch.setenv("LENSES_STICKERBOARD_LOOPBACK_DEV_AUTH", "1")
    assert stickerboard_loopback_dev_auth_enabled()
    cfg = share_public_config()
    assert cfg.get("loopback_dev_auth") is True


def test_normalize_stickerboard_api_path():
    assert normalize_stickerboard_api_path("/api/auth/status") == "/api/auth/status"
    assert (
        normalize_stickerboard_api_path("/stickerboard/api/sticker-board-share")
        == "/api/sticker-board-share"
    )
    assert normalize_stickerboard_api_path("/stickerboard/api/sticker-board") == "/api/sticker-board"


def test_share_scope_path_allowlists():
    assert share_scope_allows_path("/stickerboard/abc", "GET")
    assert share_scope_allows_path("/stickerboard/api/sticker-board-share", "POST")
    assert share_scope_allows_path("/api/sticker-board-share", "POST")
    assert not share_scope_allows_path("/api/workspace-state", "GET")
    assert stickerboard_port_allows_path("/", "GET")
    assert stickerboard_port_allows_path("/xK9mP2qR7vN4wL8sT1uH3jF", "GET")
    assert stickerboard_port_allows_path("/assets/app.js", "GET")
    assert stickerboard_port_allows_path("/stickerboard/", "GET")
    assert stickerboard_port_allows_path("/stickerboard/xK9mP2qR7vN4wL8sT1uH3jF", "GET")
    assert not stickerboard_port_allows_path("/stickerboard/", "POST")
    assert not stickerboard_port_allows_path("/studio/", "GET")
    assert not stickerboard_port_allows_path("/api/workspace-state", "GET")


def test_resolve_board_display_label_from_registry(tmp_path: Path):
    ws = _ws(tmp_path)
    reg_path = ws / ".lenses-local" / "sticker-board-registry.json"
    reg_path.write_text(
        json.dumps(
            {
                "version": REGISTRY_VERSION,
                "projects": {
                    "demo": [
                        {
                            "id": "board123456789012345678",
                            "label": "Q2 roadmap workshop",
                            "storage": "local",
                        }
                    ]
                },
            }
        ),
        encoding="utf-8",
    )
    assert (
        resolve_board_display_label(ws, "board123456789012345678")
        == "Q2 roadmap workshop"
    )


def test_share_metadata_includes_board_label(tmp_path: Path):
    ws = _ws(tmp_path)
    reg_path = ws / ".lenses-local" / "sticker-board-registry.json"
    reg_path.write_text(
        json.dumps(
            {
                "version": REGISTRY_VERSION,
                "projects": {
                    "demo": [
                        {
                            "id": "board123456789012345678",
                            "label": "Product map workshop",
                            "storage": "local",
                        }
                    ]
                },
            }
        ),
        encoding="utf-8",
    )
    result, _ = share_start(
        ws,
        board_id="board123456789012345678",
        guest_role="view",
        created_by_login="fac@example.com",
    )
    assert result
    meta, err = share_metadata(ws, result["share_token"])
    assert not err
    assert meta
    assert meta["board_label"] == "Product map workshop"


def test_resolve_share_scope_cookie(tmp_path: Path):
    ws = _ws(tmp_path)
    result, _ = share_start(
        ws,
        board_id="board123456789012345678",
        guest_role="view",
        created_by_login="fac@example.com",
    )
    assert result
    token = result["share_token"]
    cookie = f"{SHARE_SCOPE_COOKIE}={token}"
    scope = resolve_share_scope(ws, cookie)
    assert scope
    assert scope["board_id"] == "board123456789012345678"
    assert scope["guest_role"] == "view"


def test_validate_board_qualitative_labels():
    body = {
        "version": BOARD_VERSION,
        "template": "kanban",
        "board_storage": "local",
        "columns": [{"id": "a", "title": "A"}],
        "stickers": [
            {
                "id": "s1",
                "title": "T",
                "body": "",
                "column_id": "a",
                "order": 0,
                "x": 0,
                "y": 0,
                "impact_label": "strong",
                "effort_label": "quick",
            }
        ],
    }
    ok, err = validate_board(body, None)
    assert ok, err
    body["stickers"][0]["impact_label"] = "invalid"
    ok2, err2 = validate_board(body, None)
    assert not ok2
    assert "impact_label" in err2


def test_resolve_facilitator_login_loopback_open_workspace(tmp_path: Path):
    ws = _ws(tmp_path)
    login = resolve_facilitator_login(None, client_ip="127.0.0.1", workspace_root=ws)
    assert login == LOCAL_LOOPBACK_FACILITATOR_LOGIN
    assert (
        resolve_facilitator_login("owner@example.com", client_ip="127.0.0.1", workspace_root=ws)
        == "owner@example.com"
    )


def test_load_board_share_guest_without_registry(tmp_path: Path):
    ws = _ws(tmp_path)
    board_id = "board123456789012345678"
    body = {
        "version": BOARD_VERSION,
        "template": "freeform",
        "board_storage": "local",
        "columns": [{"id": "c1", "title": "Ideas"}],
        "stickers": [],
    }
    data_path = local_board_data_path(ws, board_id)
    data_path.parent.mkdir(parents=True, exist_ok=True)
    data_path.write_text(json.dumps(body), encoding="utf-8")
    board = load_board(ws, None, board_id, share_guest=True)
    assert not board.get("board_not_found")
    assert board.get("board_id") == board_id
    missing = load_board(ws, None, board_id, share_guest=False)
    assert missing.get("board_not_found")


def test_share_add_guest_acl(tmp_path: Path):
    ws = _ws(tmp_path)
    reg_path = ws / ".lenses-local" / "sticker-board-registry.json"
    reg_path.write_text(
        json.dumps(
            {
                "version": 1,
                "projects": {
                    "_unassigned": [
                        {"id": "board123456789012345678", "label": "Test", "storage": "local"}
                    ]
                },
            }
        ),
        encoding="utf-8",
    )
    assert share_add_guest_acl(ws, "board123456789012345678", "guest@example.com", "edit")
    reg = json.loads(reg_path.read_text())
    ent = reg["projects"]["_unassigned"][0]
    assert "guest@example.com" in ent.get("editors", [])
