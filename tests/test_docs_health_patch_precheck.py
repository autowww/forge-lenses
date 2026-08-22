"""Tests for docs patch deterministic precheck."""

from __future__ import annotations

from pathlib import Path

from lenses.docs_health.patch_precheck import precheck_docs_patch


def test_precheck_rejects_non_md(tmp_path: Path) -> None:
    r = precheck_docs_patch(tmp_path, project_slug="p", patch={"path": "x.txt", "content": "a"})
    assert r["ok"] is False


def test_precheck_rejects_traversal(tmp_path: Path) -> None:
    r = precheck_docs_patch(tmp_path, project_slug="p", patch={"path": "../x.md", "content": "a"})
    assert r["ok"] is False


def test_precheck_accepts_simple_md(tmp_path: Path) -> None:
    r = precheck_docs_patch(tmp_path, project_slug="p", patch={"path": "docs/a.md", "content": "# Hi\n"})
    assert r["ok"] is True
