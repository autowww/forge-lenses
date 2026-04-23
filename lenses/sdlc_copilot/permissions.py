"""RBAC helpers for copilot read vs propose-write modes."""

from __future__ import annotations

from typing import Any

from lenses.access_policy import (
    can_write_project,
    is_policy_enforced,
    is_super_admin,
)


def may_use_propose_writes(
    policy: dict[str, Any],
    login: str | None,
    project_slug: str | None,
) -> bool:
    """
    Proposing structured write drafts requires a project when RBAC is enforced,
    plus member-or-above on that project (or workspace super_admin).
    """
    slug = (project_slug or "").strip()
    if not is_policy_enforced(policy):
        return True
    if not login:
        return False
    if is_super_admin(policy, login):
        return True
    if not slug:
        return False
    return can_write_project(policy, login, slug)


def may_commit_proposal(
    policy: dict[str, Any],
    login: str | None,
    project_slug: str | None,
) -> bool:
    """Committing an approved draft uses the same gate as proposing."""
    return may_use_propose_writes(policy, login, project_slug)
