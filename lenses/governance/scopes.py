"""Fine-grained scopes derived from roles with optional per-member overrides."""

from __future__ import annotations

from typing import Any

from lenses.access_policy import (
    ROLE_DISCIPLINE_POWER,
    ROLE_MEMBER,
    ROLE_SUPER_ADMIN,
    ROLE_VIEWER,
    is_policy_enforced,
    is_super_admin,
    resolve_project_role,
)

# Resource-oriented scopes (Sprint 10 model)
SCOPE_WORKSPACE_READ = "workspace.read"
SCOPE_WORKSPACE_WRITE = "workspace.write"
SCOPE_PROJECT_READ = "project.read"
SCOPE_PROJECT_WRITE = "project.write"
SCOPE_ENVIRONMENT_READ = "environment.read"
SCOPE_RELEASE_READ = "release.read"
SCOPE_RELEASE_APPROVE = "release.approve"
SCOPE_ADMIN_POLICY = "admin.policy"
SCOPE_ADMIN_CONNECTORS = "admin.connectors"
SCOPE_ADMIN_AUDIT = "admin.audit"

_ALL_SCOPES: frozenset[str] = frozenset(
    {
        SCOPE_WORKSPACE_READ,
        SCOPE_WORKSPACE_WRITE,
        SCOPE_PROJECT_READ,
        SCOPE_PROJECT_WRITE,
        SCOPE_ENVIRONMENT_READ,
        SCOPE_RELEASE_READ,
        SCOPE_RELEASE_APPROVE,
        SCOPE_ADMIN_POLICY,
        SCOPE_ADMIN_CONNECTORS,
        SCOPE_ADMIN_AUDIT,
    }
)


def _scopes_for_role(role: str) -> frozenset[str]:
    if role == ROLE_SUPER_ADMIN:
        return _ALL_SCOPES
    if role == ROLE_DISCIPLINE_POWER:
        return frozenset(
            {
                SCOPE_WORKSPACE_READ,
                SCOPE_PROJECT_READ,
                SCOPE_PROJECT_WRITE,
                SCOPE_ENVIRONMENT_READ,
                SCOPE_RELEASE_READ,
                SCOPE_RELEASE_APPROVE,
            }
        )
    if role == ROLE_MEMBER:
        return frozenset(
            {
                SCOPE_WORKSPACE_READ,
                SCOPE_PROJECT_READ,
                SCOPE_PROJECT_WRITE,
                SCOPE_ENVIRONMENT_READ,
                SCOPE_RELEASE_READ,
            }
        )
    if role == ROLE_VIEWER:
        return frozenset(
            {
                SCOPE_WORKSPACE_READ,
                SCOPE_PROJECT_READ,
                SCOPE_ENVIRONMENT_READ,
                SCOPE_RELEASE_READ,
            }
        )
    return frozenset()


def _member_scopes_override(policy: dict[str, Any], project_slug: str, login: str) -> list[str] | None:
    from lenses.access_policy import member_record

    rec = member_record(policy, project_slug, login)
    if not rec:
        return None
    raw = rec.get("scopes")
    if not isinstance(raw, list):
        return None
    out = [str(x).strip() for x in raw if str(x).strip()]
    return out or None


def effective_scopes(
    policy: dict[str, Any],
    login: str | None,
    project_slug: str | None,
) -> tuple[list[str], str]:
    """
    Returns (sorted scope list, source) where source is ``role_derived`` or ``member_override``.
    Workspace-level (no project): super_admin gets all; else workspace.read only if any project access.
    """
    if not login:
        return [], "anonymous"
    if not is_policy_enforced(policy):
        return sorted(_ALL_SCOPES), "policy_open"

    if is_super_admin(policy, login):
        return sorted(_ALL_SCOPES), "super_admin"

    slug = (project_slug or "").strip()
    if slug:
        role, is_sa = resolve_project_role(policy, login, slug)
        if not role and not is_sa:
            return [], "no_project_access"
        override = _member_scopes_override(policy, slug, login)
        if override:
            filtered = [s for s in override if s in _ALL_SCOPES]
            return sorted(set(filtered)), "member_override"
        return sorted(_scopes_for_role(role)), "role_derived"

    # Workspace-level: union scopes across projects the user can access
    projects = policy.get("projects")
    if not isinstance(projects, dict):
        return [SCOPE_WORKSPACE_READ], "workspace_minimal"
    union: set[str] = set()
    for ps in projects:
        if not isinstance(ps, str):
            continue
        r, _ = resolve_project_role(policy, login, ps)
        if r:
            union |= set(_scopes_for_role(r))
    if not union:
        return [], "no_workspace_access"
    union.add(SCOPE_WORKSPACE_READ)
    return sorted(union), "workspace_union"


def has_scope(
    policy: dict[str, Any],
    login: str | None,
    project_slug: str | None,
    need: str,
) -> bool:
    scopes, _src = effective_scopes(policy, login, project_slug)
    return need in scopes
