"""Sticker board JSON: local file under .lenses-local/; shared mode splits repo + overlay."""

from __future__ import annotations

import json
import re
import tempfile
from pathlib import Path
from typing import Any

BOARD_VERSION = 2
BOARD_VERSION_LEGACY = 1
BOARD_FILENAME = "sticker-board.json"
SHARED_OVERLAY_FILENAME = "sticker-board-shared-local.json"
MAX_BODY_BYTES = 512 * 1024  # POST body cap (serve.py)
MAX_STICKERS = 200
MAX_TITLE_LEN = 200
MAX_BODY_LEN = 16000
MAX_COLUMNS = 8
_ID_RE = re.compile(r"^[a-zA-Z0-9_-]{1,64}$")

DEFAULT_KANBAN_COLUMNS: list[dict[str, str]] = [
    {"id": "todo", "title": "To do"},
    {"id": "doing", "title": "Doing"},
    {"id": "done", "title": "Done"},
]


def local_board_path(workspace_root: Path) -> Path:
    return workspace_root.resolve() / ".lenses-local" / BOARD_FILENAME


def shared_overlay_path(workspace_root: Path) -> Path:
    return workspace_root.resolve() / ".lenses-local" / SHARED_OVERLAY_FILENAME


def shared_repo_board_path(workspace_root: Path, github_login: str) -> Path:
    login = github_login.strip()
    return workspace_root.resolve() / ".lenses-repo" / login / BOARD_FILENAME


def default_state(template: str, board_storage: str = "local") -> dict[str, Any]:
    t = template if template in ("kanban", "freeform") else "freeform"
    bs = board_storage if board_storage in ("local", "shared") else "local"
    cols: list[dict[str, str]] = list(DEFAULT_KANBAN_COLUMNS) if t == "kanban" else []
    return {
        "version": BOARD_VERSION,
        "board_storage": bs,
        "template": t,
        "columns": cols,
        "stickers": [],
    }


def _read_json_file(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    try:
        raw = path.read_text(encoding="utf-8")
        data = json.loads(raw)
    except (OSError, json.JSONDecodeError, UnicodeError):
        return None
    return data if isinstance(data, dict) else None


def _atomic_write_json(path: Path, obj: dict[str, Any]) -> None:
    parent = path.parent
    parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(obj, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
    tmp = tempfile.NamedTemporaryFile(
        mode="w",
        encoding="utf-8",
        delete=False,
        dir=str(parent),
        prefix=".sticker-board-",
        suffix=".tmp",
    )
    tmp_path = Path(tmp.name)
    try:
        tmp.write(payload)
        tmp.close()
        tmp_path.replace(path)
    except OSError:
        try:
            tmp.close()
        except OSError:
            pass
        try:
            tmp_path.unlink(missing_ok=True)
        except OSError:
            pass
        raise


def _migrate_legacy_to_v2(data: dict[str, Any]) -> dict[str, Any]:
    if int(data.get("version", 0)) != BOARD_VERSION_LEGACY:
        return data
    out = {
        "version": BOARD_VERSION,
        "board_storage": "local",
        "template": data.get("template", "freeform"),
        "columns": data.get("columns") or [],
        "stickers": data.get("stickers") or [],
    }
    return out


def load_board(
    workspace_root: Path, expected_github_login: str | None
) -> dict[str, Any]:
    local_path = local_board_path(workspace_root)
    raw = _read_json_file(local_path)
    if raw is None:
        return default_state("freeform", "local")

    data = _migrate_legacy_to_v2(raw)
    bs = str(data.get("board_storage", "local") or "local")
    if bs not in ("local", "shared"):
        bs = "local"

    if bs == "local":
        ok, _err = validate_board(data, expected_github_login)
        if not ok:
            return default_state("freeform", "local")
        return normalize_board(data, expected_github_login)

    # shared board: marker in local file + repo + overlay
    login = (expected_github_login or "").strip()
    if not login:
        merged = normalize_board(
            {
                "version": BOARD_VERSION,
                "board_storage": "shared",
                "template": data.get("template", "freeform"),
                "columns": data.get("columns") or [],
                "stickers": [],
            },
            None,
        )
        merged["shared_board_login_required"] = True
        return merged

    repo = _read_json_file(shared_repo_board_path(workspace_root, login))
    overlay = _read_json_file(shared_overlay_path(workspace_root))

    tmpl = "freeform"
    cols: list[Any] = []
    shared_stickers: list[Any] = []
    if repo:
        repo_m = _migrate_legacy_to_v2(repo) if int(repo.get("version", 0)) == 1 else repo
        tmpl = str(repo_m.get("template", "freeform"))
        cols = list(repo_m.get("columns") or [])
        for s in repo_m.get("stickers") or []:
            if isinstance(s, dict):
                shared_stickers.append(dict(s))

    local_stickers: list[Any] = []
    if overlay:
        for s in overlay.get("stickers") or []:
            if isinstance(s, dict):
                local_stickers.append(dict(s))

    for s in shared_stickers:
        s["scope"] = "shared"
    for s in local_stickers:
        s["scope"] = "local"

    merged = {
        "version": BOARD_VERSION,
        "board_storage": "shared",
        "template": tmpl if tmpl in ("kanban", "freeform") else "freeform",
        "columns": cols,
        "stickers": shared_stickers + local_stickers,
    }
    ok, _err = validate_board(merged, login)
    if not ok:
        return default_state("freeform", "local")
    return normalize_board(merged, login)


def save_board(
    workspace_root: Path,
    state: dict[str, Any],
    expected_github_login: str | None,
) -> None:
    data = normalize_board(state, expected_github_login)
    bs = str(data.get("board_storage", "local"))

    if bs == "local":
        to_save = {
            "version": BOARD_VERSION,
            "board_storage": "local",
            "template": data["template"],
            "columns": data["columns"],
            "stickers": [],
        }
        for s in data["stickers"]:
            st = {k: v for k, v in s.items() if k != "scope"}
            to_save["stickers"].append(st)
        _atomic_write_json(local_board_path(workspace_root), to_save)
        try:
            shared_overlay_path(workspace_root).unlink(missing_ok=True)
        except OSError:
            pass
        return

    login = (expected_github_login or "").strip()
    if not login:
        raise ValueError("shared_board_login_required")

    shared_list = [s for s in data["stickers"] if s.get("scope") == "shared"]
    local_list = [s for s in data["stickers"] if s.get("scope") == "local"]

    repo_payload = {
        "version": BOARD_VERSION,
        "template": data["template"],
        "columns": data["columns"],
        "stickers": [{k: v for k, v in s.items() if k != "scope"} for s in shared_list],
    }
    overlay_payload = {
        "version": BOARD_VERSION,
        "stickers": [{k: v for k, v in s.items() if k != "scope"} for s in local_list],
    }
    marker_payload = {
        "version": BOARD_VERSION,
        "board_storage": "shared",
    }

    repo_path = shared_repo_board_path(workspace_root, login)
    _atomic_write_json(repo_path, repo_payload)
    _atomic_write_json(shared_overlay_path(workspace_root), overlay_payload)
    _atomic_write_json(local_board_path(workspace_root), marker_payload)


def normalize_board(
    data: dict[str, Any], expected_github_login: str | None
) -> dict[str, Any]:
    data = _migrate_legacy_to_v2(dict(data))
    ver = int(data.get("version", BOARD_VERSION))
    if ver == BOARD_VERSION_LEGACY:
        data = _migrate_legacy_to_v2(data)
    bs = str(data.get("board_storage", "local") or "local")
    if bs not in ("local", "shared"):
        bs = "local"

    out: dict[str, Any] = {
        "version": BOARD_VERSION,
        "board_storage": bs,
        "template": str(data.get("template", "freeform")),
        "columns": [
            {"id": str(c["id"]), "title": str(c["title"])}
            for c in (data.get("columns") or [])
            if isinstance(c, dict)
        ],
        "stickers": [],
    }
    col_ids = {c["id"] for c in out["columns"]}
    tmpl = out["template"]

    for s in data.get("stickers") or []:
        if not isinstance(s, dict):
            continue
        sid = str(s.get("id", ""))
        st: dict[str, Any] = {
            "id": sid,
            "title": str(s.get("title", "")),
            "body": str(s.get("body", "")),
            "order": int(s.get("order", 0)),
            "x": float(s.get("x", 0)),
            "y": float(s.get("y", 0)),
        }
        cid = s.get("column_id")
        if cid is None or cid == "":
            st["column_id"] = None
        else:
            st["column_id"] = str(cid)
        if tmpl == "kanban" and st["column_id"] not in col_ids:
            st["column_id"] = next(iter(col_ids), "todo")
        if bs == "shared":
            sc = s.get("scope", "shared")
            st["scope"] = "local" if sc == "local" else "shared"
        out["stickers"].append(st)
    return out


def validate_board(
    data: Any, expected_github_login: str | None
) -> tuple[bool, str]:
    if not isinstance(data, dict):
        return False, "root_must_be_object"
    raw_ver = data.get("version")
    if raw_ver not in (BOARD_VERSION, BOARD_VERSION_LEGACY):
        return False, "unsupported_version"
    tmpl = data.get("template")
    if tmpl not in ("kanban", "freeform"):
        return False, "invalid_template"

    bs = str(data.get("board_storage", "local") or "local")
    if int(raw_ver) == BOARD_VERSION_LEGACY:
        bs = "local"
    if bs not in ("local", "shared"):
        return False, "invalid_board_storage"
    if bs == "shared" and not (expected_github_login or "").strip():
        return False, "shared_board_login_required"

    cols_raw = data.get("columns")
    if cols_raw is None:
        cols_raw = []
    if not isinstance(cols_raw, list):
        return False, "columns_must_be_array"
    if len(cols_raw) > MAX_COLUMNS:
        return False, "too_many_columns"
    columns: list[dict[str, str]] = []
    seen_ids: set[str] = set()
    for c in cols_raw:
        if not isinstance(c, dict):
            return False, "column_must_be_object"
        cid = str(c.get("id", "")).strip()
        title = str(c.get("title", "")).strip()
        if not _ID_RE.match(cid):
            return False, "invalid_column_id"
        if not title or len(title) > 80:
            return False, "invalid_column_title"
        if cid in seen_ids:
            return False, "duplicate_column_id"
        seen_ids.add(cid)
        columns.append({"id": cid, "title": title})
    if tmpl == "kanban" and len(columns) < 1:
        return False, "kanban_needs_columns"

    stickers_raw = data.get("stickers")
    if stickers_raw is None:
        stickers_raw = []
    if not isinstance(stickers_raw, list):
        return False, "stickers_must_be_array"
    if len(stickers_raw) > MAX_STICKERS:
        return False, "too_many_stickers"

    col_ids = {c["id"] for c in columns}
    seen_sticker_ids: set[str] = set()
    legacy_stickers = int(raw_ver) == BOARD_VERSION_LEGACY
    for s in stickers_raw:
        if not isinstance(s, dict):
            return False, "sticker_must_be_object"
        sid = str(s.get("id", "")).strip()
        if not _ID_RE.match(sid):
            return False, "invalid_sticker_id"
        if sid in seen_sticker_ids:
            return False, "duplicate_sticker_id"
        seen_sticker_ids.add(sid)

        if not legacy_stickers:
            scope = s.get("scope", "local")
            if bs == "local":
                if scope == "shared":
                    return False, "shared_sticker_on_local_board"
            else:
                if scope not in ("local", "shared"):
                    return False, "invalid_sticker_scope"

        title = str(s.get("title", ""))
        if len(title) > MAX_TITLE_LEN:
            return False, "title_too_long"
        body = str(s.get("body", ""))
        if len(body) > MAX_BODY_LEN:
            return False, "body_too_long"
        try:
            order = int(s.get("order", 0))
        except (TypeError, ValueError):
            return False, "invalid_order"
        if order < 0 or order > 1_000_000:
            return False, "invalid_order"
        try:
            x = float(s.get("x", 0))
            y = float(s.get("y", 0))
        except (TypeError, ValueError):
            return False, "invalid_position"
        if not (-100 <= x <= 20000 and -100 <= y <= 20000):
            return False, "position_out_of_range"
        cid = s.get("column_id")
        if tmpl == "kanban":
            if cid is None or str(cid).strip() == "":
                return False, "kanban_sticker_needs_column"
            if str(cid) not in col_ids:
                return False, "unknown_column_id"
        else:
            if cid is not None and str(cid).strip() != "" and str(cid) not in col_ids:
                return False, "unknown_column_id"
    return True, ""
