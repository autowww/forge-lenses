"""Sprint 10 — governance scopes, connectors health, audit log."""

from __future__ import annotations

from pathlib import Path

import pytest

from lenses.access_policy import load_policy, save_policy
from lenses.governance.audit_log import append_event, read_recent
from lenses.governance.connectors_health import build_connectors_health
from lenses.governance.scopes import SCOPE_ADMIN_AUDIT, effective_scopes, has_scope


def test_effective_scopes_super_admin(tmp_path: Path) -> None:
    save_policy(
        tmp_path,
        {
            "bootstrap_completed": True,
            "policy_enabled": True,
            "super_admins": ["root"],
            "projects": {},
        },
    )
    pol = load_policy(tmp_path)
    scopes, src = effective_scopes(pol, "root", "any")
    assert src == "super_admin"
    assert SCOPE_ADMIN_AUDIT in scopes


def test_member_scope_override(tmp_path: Path) -> None:
    pol = {
        "bootstrap_completed": True,
        "policy_enabled": True,
        "super_admins": [],
        "projects": {
            "acme": {
                "require_explicit_membership": True,
                "members": {
                    "bob": {"role": "viewer", "scopes": ["project.read", "admin.audit"]},
                },
            },
        },
    }
    save_policy(tmp_path, pol)
    pol2 = load_policy(tmp_path)
    scopes, src = effective_scopes(pol2, "bob", "acme")
    assert src == "member_override"
    assert "admin.audit" in scopes
    assert has_scope(pol2, "bob", "acme", "admin.audit")


def test_connectors_health_schema() -> None:
    h = build_connectors_health(
        workspace_root=Path("."),
        scan_state={"children": [], "resolved_at": None},
    )
    assert h.get("ok") is True
    assert "connectors" in h
    assert isinstance(h["connectors"], list)
    for row in h["connectors"]:
        assert "id" in row and "label" in row
        assert "healthy" in row


def test_governance_audit_roundtrip(tmp_path: Path) -> None:
    eid = append_event(
        tmp_path,
        kind="data_change",
        actor="alice",
        resource="test:resource",
        detail={"k": 1},
    )
    rows = read_recent(tmp_path, limit=10)
    assert any(r.get("id") == eid for r in rows)
