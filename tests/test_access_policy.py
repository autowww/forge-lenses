"""Tests for lenses/access_policy.py and sticker board ACL helpers."""

from __future__ import annotations

from pathlib import Path

import pytest

from lenses import access_policy as ap
from lenses.sticker_board import (
    can_edit_sticker_board,
    can_manage_board_acl,
    can_view_sticker_board,
    registry_entry_acl,
)


def test_policy_enforced_only_after_bootstrap() -> None:
    assert ap.is_policy_enforced({}) is False
    assert ap.is_policy_enforced({"bootstrap_completed": True, "super_admins": ["a"]}) is True


def test_resolve_role_open_mode() -> None:
    pol = {}
    r, sup = ap.resolve_project_role(pol, "any", "forge")
    assert r == ap.ROLE_MEMBER
    assert sup is False


def test_super_admin_sees_all_projects() -> None:
    pol = {
        "version": 1,
        "bootstrap_completed": True,
        "super_admins": ["admin"],
        "projects": {},
    }
    r, sup = ap.resolve_project_role(pol, "admin", "x")
    assert sup is True
    assert r == ap.ROLE_SUPER_ADMIN


def test_explicit_member() -> None:
    pol = {
        "version": 1,
        "bootstrap_completed": True,
        "super_admins": [],
        "projects": {
            "p1": {
                "require_explicit_membership": True,
                "members": {"alice": {"role": ap.ROLE_VIEWER}},
            }
        },
    }
    r, _sup = ap.resolve_project_role(pol, "alice", "p1")
    assert r == ap.ROLE_VIEWER


def test_board_acl_view_edit() -> None:
    ent = {
        "id": "b1",
        "owner_login": "owner",
        "editors": ["ed"],
        "viewers": ["vi"],
    }
    acl = registry_entry_acl(ent)
    assert acl["owner_login"] == "owner"
    assert can_view_sticker_board(
        "vi", ent, is_workspace_super_admin=False, can_read_project=False
    )
    assert not can_view_sticker_board(
        "stranger", ent, is_workspace_super_admin=False, can_read_project=True
    )
    assert can_edit_sticker_board(
        "ed", ent, is_workspace_super_admin=False, can_write_project=False
    )
    assert can_manage_board_acl(
        "owner", ent, is_workspace_super_admin=False, can_manage_project_access=False
    )


def test_effective_project_readonly_tmp_path(tmp_path: Path) -> None:
    d = tmp_path / "r"
    d.mkdir()
    assert ap.effective_project_readonly(d) is False
