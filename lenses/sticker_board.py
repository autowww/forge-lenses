"""Sticker board JSON: per-board files under .lenses-local/sticker-boards/; shared mode splits repo + overlay."""

from __future__ import annotations

import json
import re
import secrets
import string
import tempfile
from pathlib import Path
from typing import Any

BOARD_VERSION = 2
BOARD_VERSION_LEGACY = 1
REGISTRY_VERSION = 1

# Legacy single-board filenames (migrated once into sticker-boards/<id>.*)
BOARD_FILENAME = "sticker-board.json"
SHARED_OVERLAY_FILENAME = "sticker-board-shared-local.json"
REGISTRY_FILENAME = "sticker-board-registry.json"
BOARDS_SUBDIR = "sticker-boards"
PREVIEWS_SUBDIR = "sticker-board-previews"

MAX_BODY_BYTES = 512 * 1024  # POST body cap (serve.py)
MAX_STICKERS = 200
MAX_TITLE_LEN = 200
MAX_BODY_LEN = 16000
MAX_COLUMNS = 8
MAX_BOARD_LABEL_LEN = 120
_ID_RE = re.compile(r"^[a-zA-Z0-9_-]{1,64}$")
# Board IDs are generated opaque tokens (alphanumeric + underscore).
BOARD_ID_RE = re.compile(r"^[a-zA-Z0-9_]{16,40}$")

DEFAULT_KANBAN_COLUMNS: list[dict[str, str]] = [
    {"id": "todo", "title": "To do"},
    {"id": "doing", "title": "Doing"},
    {"id": "done", "title": "Done"},
]

UNASSIGNED_PROJECT_KEY = "_unassigned"

MAX_GITHUB_LOGIN_LEN = 39
MAX_ACL_ENTRIES = 64


def _valid_github_login(s: str) -> bool:
    t = (s or "").strip()
    if not t or len(t) > MAX_GITHUB_LOGIN_LEN:
        return False
    return all(c.isalnum() or c == "-" for c in t)


def _normalize_login_list(raw: Any) -> list[str] | None:
    if raw is None:
        return None
    if not isinstance(raw, list):
        return None
    out: list[str] = []
    seen: set[str] = set()
    for x in raw[:MAX_ACL_ENTRIES]:
        if isinstance(x, str) and _valid_github_login(x):
            ln = x.strip().lower()
            if ln not in seen:
                seen.add(ln)
                out.append(ln)
    return out


def registry_entry_acl(entry: dict[str, Any]) -> dict[str, Any]:
    """Subset of registry entry for sharing UI (owner, editors, viewers)."""
    owner = str(entry.get("owner_login", "")).strip().lower()
    ed = entry.get("editors")
    vw = entry.get("viewers")
    editors = [x for x in (ed if isinstance(ed, list) else []) if isinstance(x, str)]
    viewers = [x for x in (vw if isinstance(vw, list) else []) if isinstance(x, str)]
    return {
        "owner_login": owner if owner and _valid_github_login(owner) else "",
        "editors": editors,
        "viewers": viewers,
    }


def can_view_sticker_board(
    session_login: str | None,
    entry: dict[str, Any],
    *,
    is_workspace_super_admin: bool,
    can_read_project: bool,
) -> bool:
    if is_workspace_super_admin:
        return True
    if not session_login or not session_login.strip():
        return False
    sl = session_login.strip().lower()
    acl = registry_entry_acl(entry)
    owner = acl["owner_login"]
    editors_l = {str(x).strip().lower() for x in acl["editors"] if isinstance(x, str)}
    viewers_l = {str(x).strip().lower() for x in acl["viewers"] if isinstance(x, str)}
    explicit = bool(owner) or bool(editors_l) or bool(viewers_l)
    if explicit:
        if owner and sl == owner:
            return True
        if sl in viewers_l or sl in editors_l:
            return True
        return False
    return can_read_project


def can_manage_board_acl(
    session_login: str | None,
    entry: dict[str, Any],
    *,
    is_workspace_super_admin: bool,
    can_manage_project_access: bool,
) -> bool:
    """Who may PATCH registry acl (owner, project access admin, or workspace super admin)."""
    if is_workspace_super_admin:
        return True
    if can_manage_project_access:
        return True
    if not session_login or not session_login.strip():
        return False
    sl = session_login.strip().lower()
    owner = registry_entry_acl(entry).get("owner_login") or ""
    return bool(owner) and sl == owner


def can_edit_sticker_board(
    session_login: str | None,
    entry: dict[str, Any],
    *,
    is_workspace_super_admin: bool,
    can_write_project: bool,
) -> bool:
    if is_workspace_super_admin:
        return True
    if not session_login or not session_login.strip():
        return False
    sl = session_login.strip().lower()
    acl = registry_entry_acl(entry)
    owner = acl["owner_login"]
    editors_l = {str(x).strip().lower() for x in acl["editors"] if isinstance(x, str)}
    explicit = bool(owner) or bool(editors_l)
    if explicit:
        if owner and sl == owner:
            return True
        if sl in editors_l:
            return True
        return False
    return can_write_project


def _parse_column_entries(
    raw: Any, *, array_err: str = "columns_must_be_array"
) -> tuple[list[dict[str, str]], str]:
    """Parse a columns or saved_kanban_columns array. Returns (entries, error_code)."""
    if raw is None:
        return [], ""
    if not isinstance(raw, list):
        return [], array_err
    if len(raw) > MAX_COLUMNS:
        return [], "too_many_columns"
    columns: list[dict[str, str]] = []
    seen_ids: set[str] = set()
    for c in raw:
        if not isinstance(c, dict):
            return [], "column_must_be_object"
        cid = str(c.get("id", "")).strip()
        title = str(c.get("title", "")).strip()
        if not _ID_RE.match(cid):
            return [], "invalid_column_id"
        if not title or len(title) > 80:
            return [], "invalid_column_title"
        if cid in seen_ids:
            return [], "duplicate_column_id"
        seen_ids.add(cid)
        columns.append({"id": cid, "title": title})
    return columns, ""


def _alnum_board_id(length: int = 22) -> str:
    """URL/file-safe opaque id (default 22 chars, matches BOARD_ID_RE min 16)."""
    alphabet = string.ascii_letters + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(length))


def new_board_id(workspace_root: Path) -> str:
    """Random unique board id; collision-check against existing files."""
    boards = local_boards_dir(workspace_root)
    for _ in range(80):
        bid = _alnum_board_id(22)
        if not BOARD_ID_RE.match(bid):
            continue
        if not (boards / f"{bid}.json").is_file() and not (
            boards / f"{bid}.marker.json"
        ).is_file():
            return bid
    raise RuntimeError("could_not_allocate_board_id")


def infer_single_repo_login(workspace_root: Path) -> str | None:
    """If exactly one `.lenses-repo/<login>/` exists, return that login name."""
    base = workspace_root.resolve() / ".lenses-repo"
    if not base.is_dir():
        return None
    subs = [p for p in base.iterdir() if p.is_dir()]
    if len(subs) == 1:
        return subs[0].name
    return None


def is_valid_board_id(board_id: str) -> bool:
    return bool(board_id and BOARD_ID_RE.match(board_id.strip()))


def lenses_local_dir(workspace_root: Path) -> Path:
    return workspace_root.resolve() / ".lenses-local"


def local_boards_dir(workspace_root: Path) -> Path:
    return lenses_local_dir(workspace_root) / BOARDS_SUBDIR


def board_previews_dir(workspace_root: Path) -> Path:
    return lenses_local_dir(workspace_root) / PREVIEWS_SUBDIR


def board_preview_path(workspace_root: Path, board_id: str) -> Path:
    return board_previews_dir(workspace_root) / f"{board_id.strip()}.png"


def board_preview_mtime(workspace_root: Path, board_id: str) -> float | None:
    p = board_preview_path(workspace_root, board_id)
    if not p.is_file():
        return None
    try:
        return float(p.stat().st_mtime)
    except OSError:
        return None


def registry_path(workspace_root: Path) -> Path:
    return lenses_local_dir(workspace_root) / REGISTRY_FILENAME


def local_board_path(workspace_root: Path) -> Path:
    """Legacy single-board path (pre multi-board)."""
    return lenses_local_dir(workspace_root) / BOARD_FILENAME


def shared_overlay_path(workspace_root: Path) -> Path:
    """Legacy shared overlay path."""
    return lenses_local_dir(workspace_root) / SHARED_OVERLAY_FILENAME


def shared_repo_board_path_legacy(workspace_root: Path, github_login: str) -> Path:
    login = github_login.strip()
    return workspace_root.resolve() / ".lenses-repo" / login / BOARD_FILENAME


def local_board_data_path(workspace_root: Path, board_id: str) -> Path:
    return local_boards_dir(workspace_root) / f"{board_id}.json"


def local_board_marker_path(workspace_root: Path, board_id: str) -> Path:
    return local_boards_dir(workspace_root) / f"{board_id}.marker.json"


def local_shared_overlay_path_for_board(workspace_root: Path, board_id: str) -> Path:
    return local_boards_dir(workspace_root) / f"{board_id}-shared-local.json"


def shared_repo_boards_dir(workspace_root: Path, github_login: str) -> Path:
    login = github_login.strip()
    return workspace_root.resolve() / ".lenses-repo" / login / BOARDS_SUBDIR


def shared_repo_board_path(workspace_root: Path, github_login: str, board_id: str) -> Path:
    return shared_repo_boards_dir(workspace_root, github_login) / f"{board_id}.json"


def default_state(template: str, board_storage: str = "local") -> dict[str, Any]:
    t = template if template in ("kanban", "freeform") else "freeform"
    bs = board_storage if board_storage in ("local", "shared") else "local"
    cols: list[dict[str, str]] = list(DEFAULT_KANBAN_COLUMNS) if t == "kanban" else []
    return {
        "version": BOARD_VERSION,
        "board_storage": bs,
        "template": t,
        "columns": cols,
        "saved_kanban_columns": [],
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
        "saved_kanban_columns": data.get("saved_kanban_columns") or [],
        "stickers": data.get("stickers") or [],
    }
    return out


def _default_registry() -> dict[str, Any]:
    return {"version": REGISTRY_VERSION, "projects": {}}


def load_registry_raw(workspace_root: Path) -> dict[str, Any]:
    p = registry_path(workspace_root)
    raw = _read_json_file(p)
    if raw is None:
        return _default_registry()
    if int(raw.get("version", 0) or 0) != REGISTRY_VERSION:
        return _default_registry()
    projects = raw.get("projects")
    if not isinstance(projects, dict):
        return _default_registry()
    return {"version": REGISTRY_VERSION, "projects": dict(projects)}


def board_count_for_project(workspace_root: Path, project_name: str) -> int:
    """Number of sticker boards assigned to ``project_name`` in the workspace registry."""
    try:
        root = workspace_root.resolve()
    except OSError:
        return 0
    reg = load_registry_raw(root)
    projects = reg.get("projects") or {}
    if not isinstance(projects, dict):
        return 0
    entries = projects.get(project_name)
    if not isinstance(entries, list):
        return 0
    return len(entries)


def save_registry_raw(workspace_root: Path, reg: dict[str, Any]) -> None:
    out = {
        "version": REGISTRY_VERSION,
        "projects": reg.get("projects") if isinstance(reg.get("projects"), dict) else {},
    }
    _atomic_write_json(registry_path(workspace_root), out)


def _is_legacy_shared_marker(data: dict[str, Any]) -> bool:
    if str(data.get("board_storage", "")) != "shared":
        return False
    keys = set(data.keys())
    return keys <= {"version", "board_storage"}


def _find_any_legacy_shared_repo_file(
    workspace_root: Path,
) -> tuple[str | None, Path | None]:
    """First `.lenses-repo/<login>/sticker-board.json` found (deterministic by login name)."""
    base = workspace_root.resolve() / ".lenses-repo"
    if not base.is_dir():
        return None, None
    for login_dir in sorted(base.iterdir(), key=lambda p: p.name.lower()):
        if not login_dir.is_dir():
            continue
        p = login_dir / BOARD_FILENAME
        if p.is_file():
            return login_dir.name, p
    return None, None


def ensure_legacy_migrated(
    workspace_root: Path, expected_github_login: str | None
) -> None:
    """One-time migration from single sticker-board.json to multi-board layout."""
    if registry_path(workspace_root).is_file():
        return
    legacy = local_board_path(workspace_root)
    if not legacy.is_file():
        save_registry_raw(workspace_root, _default_registry())
        return

    raw = _read_json_file(legacy)
    if raw is None:
        save_registry_raw(workspace_root, _default_registry())
        try:
            legacy.unlink(missing_ok=True)
        except OSError:
            pass
        return

    board_id = new_board_id(workspace_root)
    boards_dir = local_boards_dir(workspace_root)
    boards_dir.mkdir(parents=True, exist_ok=True)

    if _is_legacy_shared_marker(raw):
        login = (expected_github_login or "").strip() or (
            infer_single_repo_login(workspace_root) or ""
        )
        repo_old: Path | None = (
            shared_repo_board_path_legacy(workspace_root, login) if login else None
        )
        if not (login and repo_old and repo_old.is_file()):
            found_login, found_path = _find_any_legacy_shared_repo_file(workspace_root)
            if found_login and found_path is not None:
                login = found_login
                repo_old = found_path
        overlay_old = shared_overlay_path(workspace_root)

        if login and repo_old and repo_old.is_file():
            repo_new = shared_repo_board_path(workspace_root, login, board_id)
            migrated = _migrate_legacy_to_v2(_read_json_file(repo_old) or {})
            _atomic_write_json(repo_new, migrated)
            try:
                repo_old.unlink(missing_ok=True)
            except OSError:
                pass
        elif login:
            _atomic_write_json(
                shared_repo_board_path(workspace_root, login, board_id),
                {
                    "version": BOARD_VERSION,
                    "template": "freeform",
                    "columns": [],
                    "saved_kanban_columns": [],
                    "stickers": [],
                },
            )

        if overlay_old.is_file():
            ov_raw = _read_json_file(overlay_old)
            if ov_raw:
                _atomic_write_json(
                    local_shared_overlay_path_for_board(workspace_root, board_id),
                    ov_raw,
                )
            try:
                overlay_old.unlink(missing_ok=True)
            except OSError:
                pass

        marker = {"version": BOARD_VERSION, "board_storage": "shared"}
        _atomic_write_json(local_board_marker_path(workspace_root, board_id), marker)
        try:
            legacy.unlink(missing_ok=True)
        except OSError:
            pass

        reg = _default_registry()
        reg["projects"][UNASSIGNED_PROJECT_KEY] = [
            {
                "id": board_id,
                "label": "Migrated (shared)",
                "storage": "shared",
            }
        ]
        save_registry_raw(workspace_root, reg)
        return

    data = _migrate_legacy_to_v2(raw)
    bs = str(data.get("board_storage", "local") or "local")
    if bs == "shared":
        data["board_storage"] = "local"
        for s in data.get("stickers") or []:
            if isinstance(s, dict) and "scope" in s:
                del s["scope"]
    to_save = {
        "version": BOARD_VERSION,
        "board_storage": "local",
        "template": data.get("template", "freeform"),
        "columns": data.get("columns") or [],
        "saved_kanban_columns": data.get("saved_kanban_columns") or [],
        "stickers": [],
    }
    for s in data.get("stickers") or []:
        if isinstance(s, dict):
            st = {k: v for k, v in s.items() if k != "scope"}
            to_save["stickers"].append(st)
    _atomic_write_json(local_board_data_path(workspace_root, board_id), to_save)
    try:
        legacy.unlink(missing_ok=True)
    except OSError:
        pass
    try:
        shared_overlay_path(workspace_root).unlink(missing_ok=True)
    except OSError:
        pass

    reg = _default_registry()
    reg["projects"][UNASSIGNED_PROJECT_KEY] = [
        {"id": board_id, "label": "Migrated", "storage": "local"}
    ]
    save_registry_raw(workspace_root, reg)


def find_board_entry(
    reg: dict[str, Any], board_id: str
) -> tuple[str, dict[str, Any]] | None:
    projects = reg.get("projects") or {}
    if not isinstance(projects, dict):
        return None
    for proj, entries in projects.items():
        if not isinstance(entries, list):
            continue
        for e in entries:
            if not isinstance(e, dict):
                continue
            if str(e.get("id", "")) == board_id:
                return str(proj), dict(e)
    return None


def _disk_storage_mode(workspace_root: Path, board_id: str) -> str | None:
    if local_board_marker_path(workspace_root, board_id).is_file():
        return "shared"
    if local_board_data_path(workspace_root, board_id).is_file():
        return "local"
    return None


def _update_registry_entry_storage(
    workspace_root: Path, board_id: str, storage: str
) -> None:
    reg = load_registry_raw(workspace_root)
    found = find_board_entry(reg, board_id)
    if not found:
        return
    proj, _ = found
    entries = reg["projects"].setdefault(proj, [])
    if not isinstance(entries, list):
        return
    for e in entries:
        if isinstance(e, dict) and str(e.get("id", "")) == board_id:
            e["storage"] = storage
            break
    save_registry_raw(workspace_root, reg)


def load_board(
    workspace_root: Path,
    expected_github_login: str | None,
    board_id: str,
) -> dict[str, Any]:
    ensure_legacy_migrated(workspace_root, expected_github_login)
    if not is_valid_board_id(board_id):
        return default_state("freeform", "local")

    reg = load_registry_raw(workspace_root)
    if find_board_entry(reg, board_id) is None:
        return {**default_state("freeform", "local"), "board_not_found": True}

    mode = _disk_storage_mode(workspace_root, board_id)
    if mode is None:
        return {**default_state("freeform", "local"), "board_not_found": True}

    if mode == "local":
        local_path = local_board_data_path(workspace_root, board_id)
        raw = _read_json_file(local_path)
        if raw is None:
            return default_state("freeform", "local")
        data = _migrate_legacy_to_v2(raw)
        bs = str(data.get("board_storage", "local") or "local")
        if bs != "local":
            data["board_storage"] = "local"
        ok, _err = validate_board(data, expected_github_login)
        if not ok:
            return default_state("freeform", "local")
        out = normalize_board(data, expected_github_login)
        out["board_id"] = board_id
        return out

    login = (expected_github_login or "").strip()
    if not login:
        marker_raw = _read_json_file(local_board_marker_path(workspace_root, board_id))
        tmpl = "freeform"
        if marker_raw and isinstance(marker_raw.get("template"), str):
            tmpl = str(marker_raw["template"])
        merged = normalize_board(
            {
                "version": BOARD_VERSION,
                "board_storage": "shared",
                "template": tmpl,
                "columns": [],
                "saved_kanban_columns": [],
                "stickers": [],
            },
            None,
        )
        merged["shared_board_login_required"] = True
        merged["board_id"] = board_id
        return merged

    repo = _read_json_file(shared_repo_board_path(workspace_root, login, board_id))
    overlay = _read_json_file(
        local_shared_overlay_path_for_board(workspace_root, board_id)
    )

    tmpl = "freeform"
    cols: list[Any] = []
    saved_kanban_cols: list[Any] = []
    shared_stickers: list[Any] = []
    if repo:
        repo_m = _migrate_legacy_to_v2(repo) if int(repo.get("version", 0)) == 1 else repo
        tmpl = str(repo_m.get("template", "freeform"))
        cols = list(repo_m.get("columns") or [])
        saved_kanban_cols = list(repo_m.get("saved_kanban_columns") or [])
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
        "saved_kanban_columns": saved_kanban_cols,
        "stickers": shared_stickers + local_stickers,
    }
    ok, _err = validate_board(merged, login)
    if not ok:
        return default_state("freeform", "local")
    out = normalize_board(merged, login)
    out["board_id"] = board_id
    return out


def save_board(
    workspace_root: Path,
    state: dict[str, Any],
    expected_github_login: str | None,
    board_id: str,
) -> None:
    if not is_valid_board_id(board_id):
        raise ValueError("invalid_board_id")
    reg = load_registry_raw(workspace_root)
    if find_board_entry(reg, board_id) is None:
        raise ValueError("board_not_found")

    data = normalize_board(state, expected_github_login)
    bs = str(data.get("board_storage", "local"))

    local_data = local_board_data_path(workspace_root, board_id)
    marker_p = local_board_marker_path(workspace_root, board_id)
    overlay_p = local_shared_overlay_path_for_board(workspace_root, board_id)

    if bs == "local":
        to_save = {
            "version": BOARD_VERSION,
            "board_storage": "local",
            "template": data["template"],
            "columns": data["columns"],
            "saved_kanban_columns": data["saved_kanban_columns"],
            "stickers": [],
        }
        for s in data["stickers"]:
            st = {k: v for k, v in s.items() if k != "scope"}
            to_save["stickers"].append(st)
        local_boards_dir(workspace_root).mkdir(parents=True, exist_ok=True)
        _atomic_write_json(local_data, to_save)
        try:
            marker_p.unlink(missing_ok=True)
        except OSError:
            pass
        try:
            overlay_p.unlink(missing_ok=True)
        except OSError:
            pass
        _update_registry_entry_storage(workspace_root, board_id, "local")
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
        "saved_kanban_columns": data["saved_kanban_columns"],
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

    repo_path = shared_repo_board_path(workspace_root, login, board_id)
    _atomic_write_json(repo_path, repo_payload)
    _atomic_write_json(overlay_p, overlay_payload)
    _atomic_write_json(marker_p, marker_payload)
    try:
        local_data.unlink(missing_ok=True)
    except OSError:
        pass
    _update_registry_entry_storage(workspace_root, board_id, "shared")


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
        "saved_kanban_columns": [
            {"id": str(c["id"]), "title": str(c["title"])}
            for c in (data.get("saved_kanban_columns") or [])
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
        ol = s.get("owner_login")
        if isinstance(ol, str) and _valid_github_login(ol):
            st["owner_login"] = ol.strip().lower()
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

    columns, col_err = _parse_column_entries(
        data.get("columns"), array_err="columns_must_be_array"
    )
    if col_err:
        return False, col_err
    if tmpl == "kanban" and len(columns) < 1:
        return False, "kanban_needs_columns"

    saved_columns, saved_err = _parse_column_entries(
        data.get("saved_kanban_columns"),
        array_err="saved_kanban_columns_must_be_array",
    )
    if saved_err:
        return False, saved_err

    stickers_raw = data.get("stickers")
    if stickers_raw is None:
        stickers_raw = []
    if not isinstance(stickers_raw, list):
        return False, "stickers_must_be_array"
    if len(stickers_raw) > MAX_STICKERS:
        return False, "too_many_stickers"

    col_ids = {c["id"] for c in columns}
    freeform_column_ids = col_ids | {c["id"] for c in saved_columns}
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
            if cid is not None and str(cid).strip() != "":
                cid_s = str(cid).strip()
                if freeform_column_ids:
                    if cid_s not in freeform_column_ids:
                        return False, "unknown_column_id"
                elif not _ID_RE.match(cid_s):
                    return False, "invalid_column_id"
        ol = s.get("owner_login")
        if ol is not None and ol != "":
            if not isinstance(ol, str) or not _valid_github_login(ol):
                return False, "invalid_sticker_owner_login"
    return True, ""


def validate_project_key(project: str, valid_slugs: set[str]) -> bool:
    p = (project or "").strip()
    if p == UNASSIGNED_PROJECT_KEY:
        return True
    return p in valid_slugs


def registry_snapshot(
    workspace_root: Path,
    expected_github_login: str | None,
    valid_slugs: set[str],
) -> dict[str, Any]:
    ensure_legacy_migrated(workspace_root, expected_github_login)
    reg = load_registry_raw(workspace_root)
    issues: list[str] = []
    projects_out: dict[str, Any] = {}

    for proj, entries in (reg.get("projects") or {}).items():
        if not isinstance(entries, list):
            continue
        if proj != UNASSIGNED_PROJECT_KEY and proj not in valid_slugs:
            issues.append(f"unknown_project_in_registry:{proj}")
        board_list: list[dict[str, Any]] = []
        for e in entries:
            if not isinstance(e, dict):
                continue
            bid = str(e.get("id", "")).strip()
            label = str(e.get("label", "Board")).strip() or "Board"
            storage = str(e.get("storage", "local"))
            if storage not in ("local", "shared"):
                storage = "local"
            disk = _disk_storage_mode(workspace_root, bid)
            if disk is None:
                issues.append(f"missing_board_files:{bid}")
            elif disk != storage:
                issues.append(f"storage_mismatch:{bid}:{storage}->{disk}")
                storage = disk or storage
            pm = board_preview_mtime(workspace_root, bid)
            row: dict[str, Any] = {
                "id": bid,
                "label": label[:MAX_BOARD_LABEL_LEN],
                "storage": storage,
            }
            acl = registry_entry_acl(e)
            if acl.get("owner_login"):
                row["owner_login"] = acl["owner_login"]
            if acl.get("editors"):
                row["editors"] = acl["editors"]
            if acl.get("viewers"):
                row["viewers"] = acl["viewers"]
            if pm is not None:
                row["preview_mtime"] = pm
            board_list.append(row)
        projects_out[proj] = board_list

    return {
        "version": REGISTRY_VERSION,
        "projects": projects_out,
        "validation_issues": issues,
    }


def registry_apply(
    workspace_root: Path,
    expected_github_login: str | None,
    valid_slugs: set[str],
    action: str,
    payload: dict[str, Any],
    *,
    creator_login: str | None = None,
) -> tuple[bool, str, dict[str, Any] | None]:
    ensure_legacy_migrated(workspace_root, expected_github_login)
    act = (action or "").strip().lower()
    reg = load_registry_raw(workspace_root)

    if act == "create":
        project = str(payload.get("project", UNASSIGNED_PROJECT_KEY)).strip() or UNASSIGNED_PROJECT_KEY
        if not validate_project_key(project, valid_slugs):
            return False, "invalid_project", None
        label = str(payload.get("label", "New board")).strip() or "New board"
        label = label[:MAX_BOARD_LABEL_LEN]
        storage = str(payload.get("storage", "local"))
        if storage not in ("local", "shared"):
            return False, "invalid_storage", None
        if storage == "shared" and not (expected_github_login or "").strip():
            return False, "shared_board_login_required", None

        board_id = new_board_id(workspace_root)
        local_boards_dir(workspace_root).mkdir(parents=True, exist_ok=True)
        if storage == "local":
            initial = default_state("freeform", "local")
            _atomic_write_json(local_board_data_path(workspace_root, board_id), initial)
        else:
            login = (expected_github_login or "").strip()
            repo_payload = {
                "version": BOARD_VERSION,
                "template": "freeform",
                "columns": [],
                "saved_kanban_columns": [],
                "stickers": [],
            }
            _atomic_write_json(
                shared_repo_board_path(workspace_root, login, board_id),
                repo_payload,
            )
            _atomic_write_json(
                local_shared_overlay_path_for_board(workspace_root, board_id),
                {"version": BOARD_VERSION, "stickers": []},
            )
            _atomic_write_json(
                local_board_marker_path(workspace_root, board_id),
                {"version": BOARD_VERSION, "board_storage": "shared"},
            )

        reg.setdefault("projects", {})
        lst = reg["projects"].setdefault(project, [])
        if not isinstance(lst, list):
            lst = []
            reg["projects"][project] = lst
        entry: dict[str, Any] = {"id": board_id, "label": label, "storage": storage}
        cl = (creator_login or "").strip()
        if cl and _valid_github_login(cl):
            entry["owner_login"] = cl.lower()
        eds = _normalize_login_list(payload.get("editors"))
        vws = _normalize_login_list(payload.get("viewers"))
        if eds:
            entry["editors"] = eds
        if vws:
            entry["viewers"] = vws
        lst.append(entry)
        save_registry_raw(workspace_root, reg)
        return True, "", {"board_id": board_id}

    if act == "rename":
        board_id = str(payload.get("board_id", "")).strip()
        if not is_valid_board_id(board_id):
            return False, "invalid_board_id", None
        label = str(payload.get("label", "")).strip()[:MAX_BOARD_LABEL_LEN]
        if not label:
            return False, "invalid_label", None
        found = find_board_entry(reg, board_id)
        if not found:
            return False, "board_not_found", None
        proj, _ = found
        for e in reg["projects"].get(proj, []) or []:
            if isinstance(e, dict) and str(e.get("id")) == board_id:
                e["label"] = label
                break
        save_registry_raw(workspace_root, reg)
        return True, "", None

    if act == "delete":
        board_id = str(payload.get("board_id", "")).strip()
        if not is_valid_board_id(board_id):
            return False, "invalid_board_id", None
        found = find_board_entry(reg, board_id)
        if not found:
            return False, "board_not_found", None
        proj, entry = found
        storage = str(entry.get("storage", "local"))
        entries = [e for e in reg["projects"].get(proj, []) if str(e.get("id", "")) != board_id]
        reg["projects"][proj] = entries
        save_registry_raw(workspace_root, reg)

        try:
            local_board_data_path(workspace_root, board_id).unlink(missing_ok=True)
        except OSError:
            pass
        try:
            local_board_marker_path(workspace_root, board_id).unlink(missing_ok=True)
        except OSError:
            pass
        try:
            local_shared_overlay_path_for_board(workspace_root, board_id).unlink(
                missing_ok=True
            )
        except OSError:
            pass
        # Shared repo file intentionally left for team reuse (plan).
        return True, "", None

    if act == "assign":
        board_id = str(payload.get("board_id", "")).strip()
        to_project = str(payload.get("project", UNASSIGNED_PROJECT_KEY)).strip() or UNASSIGNED_PROJECT_KEY
        if not is_valid_board_id(board_id):
            return False, "invalid_board_id", None
        if not validate_project_key(to_project, valid_slugs):
            return False, "invalid_project", None
        found = find_board_entry(reg, board_id)
        if not found:
            return False, "board_not_found", None
        from_proj, entry = found
        if from_proj == to_project:
            return True, "", None
        reg["projects"][from_proj] = [
            e
            for e in reg["projects"].get(from_proj, [])
            if str(e.get("id", "")) != board_id
        ]
        reg.setdefault("projects", {})
        dest = reg["projects"].setdefault(to_project, [])
        if not isinstance(dest, list):
            dest = []
            reg["projects"][to_project] = dest
        dest.append(entry)
        save_registry_raw(workspace_root, reg)
        return True, "", None

    if act == "acl":
        board_id = str(payload.get("board_id", "")).strip()
        if not is_valid_board_id(board_id):
            return False, "invalid_board_id", None
        found = find_board_entry(reg, board_id)
        if not found:
            return False, "board_not_found", None
        proj, _ent_copy = found
        entries = reg["projects"].get(proj) or []
        ent: dict[str, Any] | None = None
        for e in entries:
            if isinstance(e, dict) and str(e.get("id", "")) == board_id:
                ent = e
                break
        if ent is None:
            return False, "board_not_found", None
        ol = payload.get("owner_login")
        if ol is not None:
            if ol == "":
                ent.pop("owner_login", None)
            elif isinstance(ol, str) and _valid_github_login(ol):
                ent["owner_login"] = ol.strip().lower()
            else:
                return False, "invalid_owner_login", None
        if "editors" in payload:
            eds = _normalize_login_list(payload.get("editors"))
            if eds is None:
                return False, "invalid_editors", None
            if eds:
                ent["editors"] = eds
            else:
                ent.pop("editors", None)
        if "viewers" in payload:
            vws = _normalize_login_list(payload.get("viewers"))
            if vws is None:
                return False, "invalid_viewers", None
            if vws:
                ent["viewers"] = vws
            else:
                ent.pop("viewers", None)
        save_registry_raw(workspace_root, reg)
        return True, "", None

    return False, "unknown_action", None
