"""Helpers for RBAC checks in serve.py (session + per-project access)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from lenses.access_policy import (
    can_read_project,
    effective_can_write_project,
    is_policy_enforced,
    load_policy,
    resolve_project_role,
)
from lenses.auth_session import SESSION_COOKIE
from lenses.scan import resolve_workspace_child_dir


def cookie_value(cookie_header: str | None, name: str) -> str | None:
    if not cookie_header:
        return None
    parts = cookie_header.split(";")
    for p in parts:
        chunk = p.strip()
        if chunk.startswith(name + "="):
            return chunk[len(name) + 1 :].strip()
    return None


def session_login(
    session_manager: Any | None, cookie_header: str | None
) -> str | None:
    if session_manager is None:
        return None
    ck = cookie_value(cookie_header, SESSION_COOKIE)
    return session_manager.session_login(ck)


def project_access_bundle(
    workspace_root: Path,
    registry: dict[str, Any],
    project_slug: str,
    session_login_val: str | None,
) -> dict[str, Any]:
    """Resolved access for one workspace child repo."""
    policy = load_policy(workspace_root)
    child = resolve_workspace_child_dir(workspace_root, project_slug, registry)
    enforced = is_policy_enforced(policy)
    out: dict[str, Any] = {
        "policy": policy,
        "enforced": enforced,
        "project_slug": project_slug,
        "session_login": session_login_val,
        "child_path": child,
        "role": "",
        "is_workspace_super_admin": False,
        "can_read_project": True,
        "can_write_project": True,
        "effective_readonly": False,
        "git_user_name": "",
        "git_user_email": "",
    }
    if child is None:
        out["can_read_project"] = False
        out["can_write_project"] = False
        return out
    if not enforced:
        from lenses.access_policy import effective_project_readonly

        er = effective_project_readonly(child)
        out["effective_readonly"] = er
        out["can_write_project"] = not er
        return out
    if not session_login_val:
        out["can_read_project"] = False
        out["can_write_project"] = False
        out["effective_readonly"] = True
        return out
    role, is_sup = resolve_project_role(policy, session_login_val, project_slug)
    out["role"] = role
    out["is_workspace_super_admin"] = is_sup
    if not role:
        out["can_read_project"] = False
        out["can_write_project"] = False
        return out
    out["can_read_project"] = can_read_project(
        policy, session_login_val, project_slug
    )
    out["can_write_project"] = effective_can_write_project(
        policy, session_login_val, project_slug, child
    )
    from lenses.access_policy import effective_project_readonly

    out["effective_readonly"] = effective_project_readonly(child)
    return out


def attach_git_identity(bundle: dict[str, Any]) -> None:
    child = bundle.get("child_path")
    if not isinstance(child, Path) or not child.is_dir():
        return
    from lenses.git_identity import git_user_identity

    name, email = git_user_identity(child)
    bundle["git_user_name"] = name
    bundle["git_user_email"] = email


def filter_sticker_registry_snapshot(
    snap: dict[str, Any],
    workspace_root: Path,
    registry: dict[str, Any],
    session_login_val: str | None,
) -> dict[str, Any]:
    """Drop boards the session may not view (when policy is enforced)."""
    from lenses.sticker_board import (
        can_view_sticker_board,
        find_board_entry,
        load_registry_raw,
        registry_entry_acl,
    )

    policy = load_policy(workspace_root)
    if not is_policy_enforced(policy):
        return snap
    raw = load_registry_raw(workspace_root)
    projects_out: dict[str, Any] = {}
    for proj, rows in (snap.get("projects") or {}).items():
        if not isinstance(rows, list):
            continue
        filtered: list[dict[str, Any]] = []
        for row in rows:
            if not isinstance(row, dict):
                continue
            bid = str(row.get("id", "")).strip()
            found = find_board_entry(raw, bid)
            if not found:
                continue
            pslug, ent = found
            bundle = project_access_bundle(
                workspace_root, registry, pslug, session_login_val
            )
            is_sup = bool(bundle.get("is_workspace_super_admin"))
            cr = bool(bundle.get("can_read_project"))
            if can_view_sticker_board(
                session_login_val,
                ent,
                is_workspace_super_admin=is_sup,
                can_read_project=cr,
            ):
                row = dict(row)
                row.update(registry_entry_acl(ent))
                filtered.append(row)
        projects_out[proj] = filtered
    out = dict(snap)
    out["projects"] = projects_out
    out["access_enforced"] = True
    return out
