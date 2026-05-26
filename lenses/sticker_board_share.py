"""Forge Lenses Stickerboard — guest share tokens and scoped access."""

from __future__ import annotations

import json
import os
import secrets
import time
from pathlib import Path
from typing import Any

SHARE_VERSION = 1
SHARES_SUBDIR = "sticker-board-shares"
SHARE_SCOPE_COOKIE = "lenses_share_scope"


def stickerboard_loopback_dev_auth_enabled() -> bool:
    """Allow localhost Stickerboard guests without Google when redirect URIs are not registered yet."""
    raw = (os.environ.get("LENSES_STICKERBOARD_LOOPBACK_DEV_AUTH") or "").strip().lower()
    return raw in ("1", "true", "yes", "on")


def normalize_stickerboard_api_path(path: str) -> str:
    """When a reverse proxy only exposes ``/stickerboard/*``, map ``/stickerboard/api/…`` → ``/api/…``."""
    p = path.split("?", 1)[0]
    if p == "/stickerboard/api" or p.startswith("/stickerboard/api/"):
        return "/api" + p[len("/stickerboard/api") :]
    return path
SHARE_TOKEN_BYTES = 24  # token_urlsafe(24) length


def shares_dir(workspace_root: Path) -> Path:
    d = workspace_root / ".lenses-local" / SHARES_SUBDIR
    d.mkdir(parents=True, exist_ok=True)
    return d


def _share_path(workspace_root: Path, token: str) -> Path:
    return shares_dir(workspace_root) / f"{token}.json"


def is_valid_share_token(token: str) -> bool:
    t = (token or "").strip()
    if len(t) < 16 or len(t) > 64:
        return False
    allowed = set("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_")
    return all(c in allowed for c in t)


def new_share_token() -> str:
    return secrets.token_urlsafe(SHARE_TOKEN_BYTES)


def _is_loopback_public_base(base: str) -> bool:
    b = (base or "").strip().lower()
    if not b:
        return False
    return "127.0.0.1" in b or "://localhost" in b or b.startswith("http://localhost")


def _load_env_file(path: Path) -> dict[str, str]:
    out: dict[str, str] = {}
    if not path.is_file():
        return out
    try:
        raw = path.read_text(encoding="utf-8")
    except OSError:
        return out
    for line in raw.splitlines():
        chunk = line.strip()
        if not chunk or chunk.startswith("#") or "=" not in chunk:
            continue
        key, _, val = chunk.partition("=")
        key = key.strip()
        if key:
            out[key] = val.strip().strip('"').strip("'")
    return out


def bootstrap_stickerboard_env_from_workspace(workspace_root: Path) -> None:
    """Load ``.lenses-local/lenses-stickerboard-local.env`` (loopback dev auth, etc.)."""
    vals = _load_env_file(workspace_root / ".lenses-local" / "lenses-stickerboard-local.env")
    for key, val in vals.items():
        if key and key not in os.environ:
            os.environ[key] = val


def bootstrap_stickerboard_public_from_workspace(workspace_root: Path) -> None:
    """
    Load ``.lenses-local/stickerboard-public.env`` when env is unset or still loopback
    (Electron defaults ``http://127.0.0.1:9999``).
    """
    vals = _load_env_file(workspace_root / ".lenses-local" / "stickerboard-public.env")
    file_base = (vals.get("LENSES_STICKERBOARD_PUBLIC_BASE") or "").strip().rstrip("/")
    if not file_base:
        return
    current = stickerboard_public_base()
    if not current or _is_loopback_public_base(current):
        os.environ["LENSES_STICKERBOARD_PUBLIC_BASE"] = file_base


def stickerboard_public_base() -> str:
    """``LENSES_STICKERBOARD_PUBLIC_BASE`` (no trailing slash), e.g. ``https://leo.forgedc.net/stickerboard``."""
    raw = (os.environ.get("LENSES_STICKERBOARD_PUBLIC_BASE") or "").strip().rstrip("/")
    return raw


def configured_stickerboard_public_base(workspace_root: Path | None = None) -> str | None:
    """Explicit non-loopback public base (env or workspace file), else ``None``."""
    env = stickerboard_public_base()
    if env and not _is_loopback_public_base(env):
        return env
    if workspace_root is not None:
        vals = _load_env_file(workspace_root / ".lenses-local" / "stickerboard-public.env")
        file_base = (vals.get("LENSES_STICKERBOARD_PUBLIC_BASE") or "").strip().rstrip("/")
        if file_base and not _is_loopback_public_base(file_base):
            return file_base
    return None


def resolved_stickerboard_public_base(workspace_root: Path | None = None) -> str:
    """
    Guest link origin: configured public base first, else local defaults.
    """
    explicit = configured_stickerboard_public_base(workspace_root)
    if explicit:
        return explicit
    base = stickerboard_public_base()
    if base:
        return base
    port_raw = (os.environ.get("LENSES_STICKERBOARD_PORT") or "9999").strip()
    try:
        sb_port = int(port_raw)
    except ValueError:
        sb_port = 9999
    host = (os.environ.get("LENSES_HOST") or "127.0.0.1").strip() or "127.0.0.1"
    if sb_port > 0:
        return f"http://{host}:{sb_port}"
    main_port = (os.environ.get("LENSES_PORT") or "8080").strip() or "8080"
    return f"http://{host}:{main_port}/stickerboard"


def share_public_config(workspace_root: Path | None = None) -> dict[str, Any]:
    """Expose configured guest base for Studio (same source as ``build_public_url``)."""
    from lenses.auth_oidc import load_oidc_config

    configured = configured_stickerboard_public_base(workspace_root)
    base = resolved_stickerboard_public_base(workspace_root)
    return {
        "ok": True,
        "public_base": base,
        "from_env": configured is not None,
        "public_base_configured": configured is not None,
        "oidc_configured": load_oidc_config() is not None,
        "loopback_dev_auth": stickerboard_loopback_dev_auth_enabled(),
    }


def build_public_url(
    token: str, *, request_origin: str | None = None, workspace_root: Path | None = None
) -> str:
    """
    ``{base}#/{token}`` — never use the Studio tab origin (Vite :5173 / random Electron port).

    ``LENSES_STICKERBOARD_PUBLIC_BASE`` wins (e.g. ``https://leo.forgedc.net/stickerboard``).
    """
    del request_origin  # unused — Host header is not a guest URL base
    return f"{resolved_stickerboard_public_base(workspace_root).rstrip('/')}/#/{token}"


def load_share(workspace_root: Path, token: str) -> dict[str, Any] | None:
    if not is_valid_share_token(token):
        return None
    path = _share_path(workspace_root, token)
    if not path.is_file():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(data, dict):
        return None
    if data.get("revoked"):
        return None
    return data


def save_share(workspace_root: Path, token: str, data: dict[str, Any]) -> None:
    path = _share_path(workspace_root, token)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")
    tmp.replace(path)


def share_start(
    workspace_root: Path,
    *,
    board_id: str,
    guest_role: str,
    created_by_login: str,
    request_origin: str | None = None,
) -> tuple[dict[str, Any] | None, str]:
    """Create share record. Returns (result_dict, error_code)."""
    role = (guest_role or "").strip().lower()
    if role not in ("view", "edit"):
        return None, "invalid_guest_role"
    bid = (board_id or "").strip()
    if not bid:
        return None, "missing_board_id"
    login = (created_by_login or "").strip()
    if not login:
        return None, "login_required"
    token = new_share_token()
    now = int(time.time())
    record: dict[str, Any] = {
        "version": SHARE_VERSION,
        "board_id": bid,
        "guest_role": role,
        "created_at": now,
        "created_by_login": login,
        "revoked": False,
        "participants": [],
    }
    save_share(workspace_root, token, record)
    return (
        {
            "ok": True,
            "share_token": token,
            "public_url": build_public_url(
                token, request_origin=request_origin, workspace_root=workspace_root
            ),
            "guest_role": role,
            "board_id": bid,
        },
        "",
    )


def share_revoke(
    workspace_root: Path,
    *,
    share_token: str,
    actor_login: str,
) -> tuple[bool, str]:
    rec = load_share(workspace_root, share_token)
    if not rec:
        return False, "share_not_found"
    creator = str(rec.get("created_by_login") or "").strip().lower()
    if creator and creator != (actor_login or "").strip().lower():
        return False, "share_revoke_forbidden"
    rec["revoked"] = True
    rec["revoked_at"] = int(time.time())
    save_share(workspace_root, share_token, rec)
    return True, ""


def share_metadata(
    workspace_root: Path, token: str
) -> tuple[dict[str, Any] | None, str]:
    from lenses.sticker_board import (
        find_board_entry,
        load_registry_raw,
        resolve_board_display_label,
    )

    rec = load_share(workspace_root, token)
    if not rec:
        return None, "share_not_found"
    board_id = str(rec.get("board_id") or "").strip()
    reg_ent: dict[str, Any] | None = None
    if board_id:
        found = find_board_entry(load_registry_raw(workspace_root), board_id)
        if found:
            reg_ent = found[1]
    board_label = (
        resolve_board_display_label(
            workspace_root,
            board_id,
            registry_entry=reg_ent,
        )
        if board_id
        else ""
    )
    return (
        {
            "ok": True,
            "board_id": board_id,
            "board_label": board_label,
            "guest_role": rec.get("guest_role"),
            "revoked": bool(rec.get("revoked")),
            "participants": rec.get("participants") or [],
            "created_at": rec.get("created_at"),
        },
        "",
    )


def share_join(
    workspace_root: Path,
    *,
    share_token: str,
    login: str,
    display_name: str | None = None,
    email: str | None = None,
) -> tuple[dict[str, Any] | None, str]:
    rec = load_share(workspace_root, share_token)
    if not rec:
        return None, "share_not_found"
    if rec.get("revoked"):
        return None, "share_revoked"
    sl = (login or "").strip().lower()
    if not sl:
        return None, "login_required"
    role = str(rec.get("guest_role") or "view").strip().lower()
    participants: list[dict[str, Any]] = list(rec.get("participants") or [])
    dn = (display_name or email or login or "").strip() or sl
    em = (email or "").strip().lower() or None
    found = False
    for p in participants:
        if isinstance(p, dict) and str(p.get("login", "")).strip().lower() == sl:
            p["display_name"] = dn
            if em:
                p["email"] = em
            p["joined_at"] = int(time.time())
            found = True
            break
    if not found:
        row: dict[str, Any] = {
            "login": sl,
            "display_name": dn,
            "joined_at": int(time.time()),
        }
        if em:
            row["email"] = em
        participants.append(row)
    rec["participants"] = participants
    save_share(workspace_root, share_token, rec)
    return (
        {
            "ok": True,
            "board_id": rec.get("board_id"),
            "guest_role": role,
            "share_token": share_token,
        },
        "",
    )


def parse_share_scope_cookie(cookie_header: str | None) -> dict[str, str] | None:
    """Return {token, board_id, guest_role} from HttpOnly cookie value (= share token)."""
    if not cookie_header:
        return None
    for part in cookie_header.split(";"):
        p = part.strip()
        if not p.startswith(f"{SHARE_SCOPE_COOKIE}="):
            continue
        token = p.split("=", 1)[1].strip()
        if not is_valid_share_token(token):
            return None
        return {"token": token}
    return None


def resolve_share_scope(
    workspace_root: Path, cookie_header: str | None
) -> dict[str, str] | None:
    """Attach board_id and guest_role from token file."""
    partial = parse_share_scope_cookie(cookie_header)
    if not partial:
        return None
    rec = load_share(workspace_root, partial["token"])
    if not rec:
        return None
    return {
        "token": partial["token"],
        "board_id": str(rec.get("board_id") or "").strip(),
        "guest_role": str(rec.get("guest_role") or "view").strip().lower(),
    }


def share_scope_allows_path(path: str, method: str) -> bool:
    """Paths allowed when lenses_share_scope cookie is active (main port)."""
    p = normalize_stickerboard_api_path(path).split("?", 1)[0].rstrip("/") or "/"
    if p.startswith("/__ks/"):
        return True
    if p.startswith("/stickerboard/assets/"):
        return True
    if p == "/stickerboard" or p.startswith("/stickerboard/"):
        return True
    if p.startswith("/api/sticker-board-share"):
        return True
    if p == "/api/sticker-board" and method in ("GET", "POST"):
        return True
    if p == "/api/auth/status":
        return True
    if p.startswith("/api/auth/oidc"):
        return True
    if p == "/api/auth/loopback-dev-login" and method == "POST":
        return True
    if p == "/api/auth/logout":
        return True
    return False


def stickerboard_port_allows_path(path: str, method: str) -> bool:
    """Allowlist for dedicated local listener (:9999) — app at site root, no ``/stickerboard`` prefix."""
    p = normalize_stickerboard_api_path(path).split("?", 1)[0].rstrip("/") or "/"
    if p.startswith("/__ks/"):
        return True
    if p.startswith("/assets/"):
        return True
    if p.startswith("/api/sticker-board-share"):
        return True
    if p == "/api/sticker-board" and method in ("GET", "POST"):
        return True
    if p == "/api/auth/status":
        return True
    if p.startswith("/api/auth/oidc"):
        return True
    if p == "/api/auth/loopback-dev-login" and method == "POST":
        return True
    if p == "/api/auth/logout":
        return True
    if p.startswith("/studio"):
        return False
    if p.startswith("/api/"):
        return False
    # Reverse proxies may forward ``/stickerboard/*`` to the dedicated listener.
    if p.startswith("/stickerboard"):
        return method == "GET"
    return True
