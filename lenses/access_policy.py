"""Per-project RBAC policy stored under .lenses-local/lenses-access.json (gitignored)."""

from __future__ import annotations

import json
import os
import tempfile
import threading
from pathlib import Path
from typing import Any

ACCESS_POLICY_VERSION = 1
POLICY_FILENAME = "lenses-access.json"

# Role names (per project unless super_admin)
ROLE_SUPER_ADMIN = "super_admin"
ROLE_DISCIPLINE_POWER = "discipline_power_user"
ROLE_MEMBER = "member"
ROLE_VIEWER = "viewer"

_ROLE_RANK: dict[str, int] = {
    ROLE_VIEWER: 0,
    ROLE_MEMBER: 1,
    ROLE_DISCIPLINE_POWER: 2,
    ROLE_SUPER_ADMIN: 3,
}


def policy_path(workspace_root: Path) -> Path:
    return workspace_root.resolve() / ".lenses-local" / POLICY_FILENAME


def _atomic_write(path: Path, obj: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    raw = json.dumps(obj, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
    tmp = tempfile.NamedTemporaryFile(
        mode="w",
        encoding="utf-8",
        delete=False,
        dir=str(path.parent),
        prefix=".lenses-access-",
        suffix=".tmp",
    )
    tmp_path = Path(tmp.name)
    try:
        tmp.write(raw)
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


_policy_lock = threading.Lock()
_cache: dict[str, tuple[float, dict[str, Any]]] = {}


def _cache_key(workspace_root: Path) -> str:
    return str(workspace_root.resolve())


def load_policy(workspace_root: Path, *, use_cache: bool = True) -> dict[str, Any]:
    """Load policy; return empty dict if missing (legacy open mode)."""
    key = _cache_key(workspace_root)
    p = policy_path(workspace_root)
    try:
        mtime = p.stat().st_mtime
    except OSError:
        mtime = 0.0
    if use_cache and mtime:
        with _policy_lock:
            hit = _cache.get(key)
            if hit is not None and hit[0] == mtime:
                return dict(hit[1])
    if not p.is_file():
        return {}
    try:
        raw = p.read_text(encoding="utf-8")
        data = json.loads(raw)
    except (OSError, json.JSONDecodeError):
        return {}
    if not isinstance(data, dict):
        return {}
    with _policy_lock:
        if mtime:
            _cache[key] = (mtime, dict(data))
    return data


def invalidate_policy_cache(workspace_root: Path) -> None:
    with _policy_lock:
        _cache.pop(_cache_key(workspace_root), None)


def save_policy(workspace_root: Path, data: dict[str, Any]) -> None:
    data = dict(data)
    data["version"] = ACCESS_POLICY_VERSION
    p = policy_path(workspace_root)
    _atomic_write(p, data)
    invalidate_policy_cache(workspace_root)
    try:
        mtime = p.stat().st_mtime
        with _policy_lock:
            _cache[_cache_key(workspace_root)] = (mtime, dict(data))
    except OSError:
        pass


def is_policy_enforced(policy: dict[str, Any]) -> bool:
    """After bootstrap, access checks apply."""
    if not policy:
        return False
    if policy.get("policy_enabled") is False:
        return False
    return bool(policy.get("bootstrap_completed"))


def normalize_login(login: str) -> str:
    return (login or "").strip().lower()


def _super_admins(policy: dict[str, Any]) -> set[str]:
    raw = policy.get("super_admins")
    if not isinstance(raw, list):
        return set()
    return {normalize_login(x) for x in raw if isinstance(x, str) and x.strip()}


def is_super_admin(policy: dict[str, Any], login: str) -> bool:
    return normalize_login(login) in _super_admins(policy)


def _project_config(policy: dict[str, Any], project_slug: str) -> dict[str, Any]:
    projects = policy.get("projects")
    if not isinstance(projects, dict):
        return {}
    cfg = projects.get(project_slug)
    return cfg if isinstance(cfg, dict) else {}


def member_record(policy: dict[str, Any], project_slug: str, login: str) -> dict[str, Any] | None:
    cfg = _project_config(policy, project_slug)
    members = cfg.get("members")
    if not isinstance(members, dict):
        return None
    ln = normalize_login(login)
    for k, v in members.items():
        if isinstance(k, str) and normalize_login(k) == ln:
            return v if isinstance(v, dict) else {}
    return None


def listed_in_any_project(policy: dict[str, Any], login: str) -> bool:
    """True if login appears in any project's members map."""
    ln = normalize_login(login)
    projects = policy.get("projects")
    if not isinstance(projects, dict):
        return False
    for _slug, cfg in projects.items():
        if not isinstance(cfg, dict):
            continue
        members = cfg.get("members")
        if not isinstance(members, dict):
            continue
        for k in members:
            if isinstance(k, str) and normalize_login(k) == ln:
                return True
    return False


def can_sign_in(policy: dict[str, Any], login: str) -> bool:
    """Whether this GitHub login may establish a session."""
    if not is_policy_enforced(policy):
        return True
    ln = normalize_login(login)
    if ln in _super_admins(policy):
        return True
    if listed_in_any_project(policy, login):
        return True
    return False


def resolve_project_role(
    policy: dict[str, Any], login: str, project_slug: str
) -> tuple[str, bool]:
    """
    Returns (role, is_workspace_super_admin).
    Role is one of ROLE_*; empty string means no access.
    """
    if not is_policy_enforced(policy):
        return ROLE_MEMBER, False
    if is_super_admin(policy, login):
        return ROLE_SUPER_ADMIN, True
    cfg = _project_config(policy, project_slug)
    rec = member_record(policy, project_slug, login)
    if rec is not None:
        r = str(rec.get("role", ROLE_MEMBER)).strip()
        if r not in _ROLE_RANK:
            r = ROLE_MEMBER
        return r, False
    require_explicit = cfg.get("require_explicit_membership")
    if require_explicit is None:
        require_explicit = True
    if not require_explicit:
        dr = str(cfg.get("default_role", ROLE_VIEWER)).strip()
        if dr not in _ROLE_RANK:
            dr = ROLE_VIEWER
        return dr, False
    return "", False


def role_at_least(have: str, need: str) -> bool:
    return _ROLE_RANK.get(have, -1) >= _ROLE_RANK.get(need, 0)


def can_read_project(policy: dict[str, Any], login: str | None, project_slug: str) -> bool:
    if not is_policy_enforced(policy):
        return True
    if not login:
        return False
    role, _ = resolve_project_role(policy, login, project_slug)
    if not role:
        return False
    return role_at_least(role, ROLE_VIEWER)


def can_write_project(policy: dict[str, Any], login: str | None, project_slug: str) -> bool:
    if not is_policy_enforced(policy):
        return True
    if not login:
        return False
    role, _ = resolve_project_role(policy, login, project_slug)
    if not role:
        return False
    return role_at_least(role, ROLE_MEMBER)


def can_manage_access(policy: dict[str, Any], login: str | None, project_slug: str) -> bool:
    if not is_policy_enforced(policy):
        return bool(login)
    if not login:
        return False
    if is_super_admin(policy, login):
        return True
    role, _ = resolve_project_role(policy, login, project_slug)
    return role_at_least(role, ROLE_DISCIPLINE_POWER)


def effective_can_write_project(
    policy: dict[str, Any],
    login: str | None,
    project_slug: str,
    project_path: Path,
) -> bool:
    if not can_write_project(policy, login, project_slug):
        return False
    return not effective_project_readonly(project_path)


def effective_project_readonly(project_path: Path) -> bool:
    """True if the repo directory is not writable (mutations should be blocked)."""
    try:
        p = project_path.resolve()
        if not p.is_dir():
            return True
        return not os.access(p, os.W_OK)
    except OSError:
        return True


def bootstrap_on_first_auth(workspace_root: Path, login: str) -> dict[str, Any]:
    """
    If no policy file exists, create one with super_admins=[login] and policy_enabled.
    Returns the current policy after any bootstrap.
    """
    p = policy_path(workspace_root)
    if p.is_file():
        pol = load_policy(workspace_root, use_cache=False)
        if pol.get("bootstrap_completed"):
            return pol
        # Partial file — ensure bootstrap flag
        if not pol.get("super_admins"):
            pol["super_admins"] = [login]
        pol["bootstrap_completed"] = True
        pol["policy_enabled"] = True
        save_policy(workspace_root, pol)
        return pol
    pol = {
        "version": ACCESS_POLICY_VERSION,
        "bootstrap_completed": True,
        "policy_enabled": True,
        "super_admins": [login],
        "projects": {},
    }
    save_policy(workspace_root, pol)
    return pol


def set_project_member(
    policy: dict[str, Any],
    project_slug: str,
    login: str,
    *,
    role: str,
    disciplines: list[str] | None = None,
    scopes: list[str] | None = None,
) -> dict[str, Any]:
    """Return updated policy dict (member keys are normalized lowercase)."""
    pol = dict(policy)
    projects = dict(pol.get("projects") or {})
    cfg = dict(projects.get(project_slug) or {})
    members = dict(cfg.get("members") or {})
    entry: dict[str, Any] = {"role": role}
    if disciplines is not None:
        entry["disciplines"] = list(disciplines)
    if scopes is not None:
        entry["scopes"] = [str(s).strip() for s in scopes if str(s).strip()]
    members[normalize_login(login)] = entry
    cfg["members"] = members
    projects[project_slug] = cfg
    pol["projects"] = projects
    return pol


def remove_project_member(policy: dict[str, Any], project_slug: str, login: str) -> dict[str, Any]:
    pol = dict(policy)
    projects = dict(pol.get("projects") or {})
    cfg = dict(projects.get(project_slug) or {})
    members = dict(cfg.get("members") or {})
    lk = normalize_login(login)
    members = {k: v for k, v in members.items() if not (isinstance(k, str) and normalize_login(k) == lk)}
    cfg["members"] = members
    projects[project_slug] = cfg
    pol["projects"] = projects
    return pol


def power_user_may_assign_disciplines(
    policy: dict[str, Any], admin_login: str, project_slug: str, assign_disciplines: list[str]
) -> bool:
    """Discipline power user can only assign disciplines that overlap their own."""
    if is_super_admin(policy, admin_login):
        return True
    rec = member_record(policy, project_slug, admin_login)
    if not rec:
        return False
    if str(rec.get("role", "")).strip() != ROLE_DISCIPLINE_POWER:
        return False
    mine = rec.get("disciplines")
    if not isinstance(mine, list) or not mine:
        return False
    mine_set = {str(x).strip() for x in mine if str(x).strip()}
    assign_set = {str(x).strip() for x in assign_disciplines if str(x).strip()}
    return bool(mine_set & assign_set) or assign_set <= mine_set
