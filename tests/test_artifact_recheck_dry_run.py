"""Tests for artifact recheck dry_run (no persistence)."""

from __future__ import annotations

import tempfile
from pathlib import Path

from lenses.blueprints_wizard.api import post_artifact_recheck
from lenses.blueprints_wizard.artifact_recheck_service import run_artifact_recheck
from lenses.blueprints_wizard.session_store import create_session, load_session
from lenses.blueprints_wizard.wizard_domain_normalize import normalize_wizard_domain


def test_run_artifact_recheck_dry_run_skips_save() -> None:
    root = Path(tempfile.mkdtemp(prefix="lenses-recheck-dry-"))
    sid = create_session(root)
    doc0 = load_session(root, sid)
    assert doc0 is not None
    wd0 = normalize_wizard_domain(doc0.payload.get("wizard_domain"))

    out = run_artifact_recheck(root, sid, {"dry_run": True})
    assert out.get("ok") is True
    assert out.get("dry_run") is True
    assert "session" not in out
    assert out.get("recheck_summary", {}).get("report", {}).get("schema_version") == 1

    doc1 = load_session(root, sid)
    assert doc1 is not None
    wd1 = normalize_wizard_domain(doc1.payload.get("wizard_domain"))
    assert wd1["recheck_summary"]["checked_at"] == wd0["recheck_summary"]["checked_at"]
    assert wd1["recheck_summary"]["passed"] == wd0["recheck_summary"]["passed"]


def test_run_artifact_recheck_persist_sets_session() -> None:
    root = Path(tempfile.mkdtemp(prefix="lenses-recheck-save-"))
    sid = create_session(root)
    out = run_artifact_recheck(root, sid, {})
    assert out.get("ok") is True
    assert out.get("dry_run") is False
    assert "session" in out
    doc = load_session(root, sid)
    assert doc is not None
    rs = normalize_wizard_domain(doc.payload.get("wizard_domain"))["recheck_summary"]
    assert rs.get("report", {}).get("schema_version") == 1


def test_post_artifact_recheck_api_dry_run() -> None:
    root = Path(tempfile.mkdtemp(prefix="lenses-recheck-api-"))
    sid = create_session(root)
    r = post_artifact_recheck(root, sid, {"dry_run": 1})
    assert r.get("ok") is True
    assert r.get("dry_run") is True
