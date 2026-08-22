"""Tests for wizard session list, scope validation, and GitHub helper (no network)."""

from __future__ import annotations

from pathlib import Path

import pytest

from lenses.blueprints_wizard.api import get_sessions_list, put_session
from lenses.blueprints_wizard.github_create import create_github_repo_http
from lenses.blueprints_wizard.schemas import WizardSessionDocument, normalize_wizard_payload
from lenses.blueprints_wizard.session_store import create_session, load_session, session_file


def test_list_sessions_empty(tmp_path: Path) -> None:
    out = get_sessions_list(tmp_path)
    assert out["ok"] is True
    assert out["sessions"] == []


def test_list_sessions_after_create(tmp_path: Path) -> None:
    sid = create_session(tmp_path)
    out = get_sessions_list(tmp_path)
    assert len(out["sessions"]) == 1
    assert out["sessions"][0]["session_id"] == sid


def test_put_rejects_bad_wbs_rel(tmp_path: Path) -> None:
    sid = create_session(tmp_path)
    doc = load_session(tmp_path, sid)
    assert doc is not None
    body = doc.to_dict()
    body["payload"] = normalize_wizard_payload(
        {
            **body["payload"],
            "scope": {"wbs_rel": "../../../etc/passwd", "roadmap_rel": None},
        }
    )
    r = put_session(tmp_path, sid, body)
    assert r["ok"] is False
    assert r.get("error") == "invalid_wbs_rel"


def test_put_rejects_run_plan_too_many_steps(tmp_path: Path) -> None:
    sid = create_session(tmp_path)
    doc = load_session(tmp_path, sid)
    assert doc is not None
    body = doc.to_dict()
    steps = [{"id": f"s{i}", "title": f"t{i}", "detail": ""} for i in range(33)]
    wd = dict(body["payload"]["wizard_domain"])
    wd["run_plan"] = {"id": "rp", "title": "x", "steps": steps}
    pl = {**body["payload"], "wizard_domain": wd}
    body["payload"] = normalize_wizard_payload(pl)
    r = put_session(tmp_path, sid, body)
    assert r["ok"] is False
    assert r.get("error") == "run_plan_too_many_steps"


def test_put_accepts_valid_scope_when_files_exist(tmp_path: Path) -> None:
    req = tmp_path / "some" / "docs" / "requirements"
    req.mkdir(parents=True)
    (req / "WBS.md").write_text("# WBS\n", encoding="utf-8")
    docs = tmp_path / "x" / "docs"
    docs.mkdir(parents=True)
    (docs / "ROADMAP.md").write_text("# R\n", encoding="utf-8")
    sid = create_session(tmp_path)
    doc = load_session(tmp_path, sid)
    assert doc is not None
    wbs_rel = str((req / "WBS.md").relative_to(tmp_path)).replace("\\", "/")
    rm_rel = str((docs / "ROADMAP.md").relative_to(tmp_path)).replace("\\", "/")
    body = doc.to_dict()
    body["payload"] = normalize_wizard_payload(
        {**body["payload"], "scope": {"wbs_rel": wbs_rel, "roadmap_rel": rm_rel}}
    )
    r = put_session(tmp_path, sid, body)
    assert r["ok"] is True


def test_github_create_http_missing_token() -> None:
    r = create_github_repo_http(
        token="",
        repo_name="r",
        description="",
        private=True,
        owner="u",
        account_type="user",
    )
    assert r["ok"] is False
    assert r.get("error") == "missing_github_token"


def test_post_create_repo_requires_confirm(tmp_path: Path) -> None:
    from lenses.blueprints_wizard.api import post_create_repo
    from lenses.blueprints_wizard.session_store import create_session

    sid = create_session(tmp_path)
    r = post_create_repo(tmp_path, sid, {})
    assert r.get("ok") is False
    assert r.get("error") == "confirmation_required"
