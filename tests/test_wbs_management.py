"""Tests for WBS management helpers and create flow."""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from lenses.wbs_management import (
    WORKSPACE_PROJECT_KEY,
    build_wbs_management_payload,
    build_wbs_project_rows,
    create_wbs_md,
    partition_wbs_by_project,
    prepare_wbs_body,
    validate_tag_name,
)


def test_validate_tag_name() -> None:
    assert validate_tag_name("v1.0.0")
    assert validate_tag_name("release/2024-01")
    assert not validate_tag_name("")
    assert not validate_tag_name("bad tag")


def test_partition_workspace_docs_vs_children() -> None:
    state = {
        "children": [{"name": "alpha", "path": "/x/alpha", "is_git": True, "git": {}}],
        "wbs": [
            {"repo_hint": "docs", "rel_path": "docs/requirements/WBS.md", "kind": "md"},
            {"repo_hint": "alpha", "rel_path": "alpha/docs/requirements/WBS.md", "kind": "md"},
        ],
    }
    by_hint, orphan = partition_wbs_by_project(state)
    assert len(orphan) == 1
    assert by_hint["alpha"]
    assert orphan[0]["rel_path"] == "docs/requirements/WBS.md"


def test_partition_docs_child_steals_workspace_hint() -> None:
    state = {
        "children": [{"name": "docs", "path": "/x/docs", "is_git": True, "git": {}}],
        "wbs": [
            {"repo_hint": "docs", "rel_path": "docs/docs/requirements/WBS.md", "kind": "md"},
        ],
    }
    by_hint, orphan = partition_wbs_by_project(state)
    assert orphan == []
    assert by_hint["docs"]


def test_build_rows_order_workspace_first(tmp_path: Path) -> None:
    state = {
        "workspace_root": str(tmp_path),
        "children": [{"name": "zoo", "path": str(tmp_path / "zoo"), "is_git": False, "git": {}}],
        "wbs": [
            {"repo_hint": "docs", "rel_path": "docs/requirements/WBS.md", "kind": "md"},
        ],
    }
    rows = build_wbs_project_rows(state)
    assert rows[0].key == WORKSPACE_PROJECT_KEY
    assert rows[1].key == "zoo"


def test_prepare_wbs_body_replaces_title_and_date() -> None:
    tpl = "| **Product / initiative** | |\n| **Date** | YYYY-MM-DD |\n| **Status** | Draft / Baselined / Updated |\n"
    body = prepare_wbs_body(
        "# Work breakdown structure — [X]\n\n" + tpl,
        "MyProduct",
        baseline_release="v2.0.0",
        today="2030-01-15",
    )
    assert "MyProduct" in body
    assert "2030-01-15" in body
    assert "**Release baseline**" in body
    assert "v2.0.0" in body


def test_create_wbs_md(tmp_path: Path) -> None:
    repo = tmp_path / "proj"
    repo.mkdir()
    subprocess.run(["git", "init", "-b", "main", str(repo)], check=True, capture_output=True)
    lenses_root = tmp_path / "lenses_stub"
    lenses_root.mkdir()
    (lenses_root / "blueprints" / "pdlc" / "templates").mkdir(parents=True)
    (lenses_root / "blueprints" / "pdlc" / "templates" / "WBS.template.md").write_text(
        load_min_template(),
        encoding="utf-8",
    )
    reg: dict = {}
    r = create_wbs_md(
        tmp_path,
        reg,
        lenses_root,
        "proj",
        baseline_tag="v0.1.0",
        new_tag=None,
    )
    assert r["ok"] is True
    p = repo / "docs" / "requirements" / "WBS.md"
    assert p.is_file()
    text = p.read_text(encoding="utf-8")
    assert "proj" in text or "Product" in text


def load_min_template() -> str:
    return (
        "# Work breakdown structure — [Product / Initiative Name]\n\n"
        "## 1. Overview\n\n"
        "| Field | Detail |\n|-------|--------|\n"
        "| **Product / initiative** | |\n"
        "| **Date** | YYYY-MM-DD |\n"
        "| **Status** | Draft / Baselined / Updated |\n"
    )


def test_build_wbs_management_payload(tmp_path: Path) -> None:
    repo = tmp_path / "r1"
    repo.mkdir()
    subprocess.run(["git", "init", "-b", "main", str(repo)], check=True, capture_output=True)
    (repo / "README.md").write_text("x", encoding="utf-8")
    subprocess.run(["git", "-C", str(repo), "add", "README.md"], check=True, capture_output=True)
    subprocess.run(
        ["git", "-C", str(repo), "commit", "-m", "init"],
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "-C", str(repo), "tag", "-a", "v9", "-m", "t"],
        check=True,
        capture_output=True,
    )
    state = {
        "workspace_root": str(tmp_path),
        "children": [{"name": "r1", "path": str(repo), "is_git": True, "git": {}}],
        "wbs": [],
    }
    payload = build_wbs_management_payload(tmp_path, {}, state)
    assert len(payload["projects"]) == 1
    p0 = payload["projects"][0]
    assert p0["key"] == "r1"
    assert "v9" in p0["tags"]
    assert p0["has_wbs_md"] is False
