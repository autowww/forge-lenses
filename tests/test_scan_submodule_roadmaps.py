"""Roadmap discovery must not include ROADMAP.md inside another repo's git submodule tree."""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from lenses.scan import scan_workspace


def _git_init(path: Path) -> None:
    subprocess.run(
        ["git", "init"],
        cwd=path,
        check=True,
        capture_output=True,
    )


@pytest.mark.skipif(
    subprocess.run(["git", "--version"], capture_output=True).returncode != 0,
    reason="git not available",
)
def test_roadmap_scan_skips_git_submodule_paths(tmp_path: Path) -> None:
    workspace = tmp_path / "ws"
    workspace.mkdir()
    lenses_fake = tmp_path / "forge-lenses"
    lenses_fake.mkdir()

    proj = workspace / "myapp"
    proj.mkdir()
    _git_init(proj)

    (proj / ".gitmodules").write_text(
        '[submodule "bp"]\n\tpath = vendor/bp\n\turl = https://example.com/bp.git\n',
        encoding="utf-8",
    )
    main_docs = proj / "docs"
    main_docs.mkdir(parents=True)
    (main_docs / "ROADMAP.md").write_text("# Main product roadmap\n", encoding="utf-8")

    sub_tree = proj / "vendor" / "bp" / "docs"
    sub_tree.mkdir(parents=True)
    (sub_tree / "ROADMAP.md").write_text("# Submodule roadmap — should not appear\n", encoding="utf-8")

    state = scan_workspace(workspace, lenses_fake, {})
    rels = [r["rel_path"] for r in state.get("roadmaps") or []]

    assert "myapp/docs/ROADMAP.md" in rels
    assert not any("vendor/bp" in r for r in rels), rels


@pytest.mark.skipif(
    subprocess.run(["git", "--version"], capture_output=True).returncode != 0,
    reason="git not available",
)
def test_roadmap_scan_lists_nested_roadmap_without_gitmodules(tmp_path: Path) -> None:
    workspace = tmp_path / "ws"
    workspace.mkdir()
    lenses_fake = tmp_path / "forge-lenses"
    lenses_fake.mkdir()

    proj = workspace / "app"
    proj.mkdir()
    _git_init(proj)

    (proj / "docs").mkdir(parents=True)
    (proj / "docs" / "ROADMAP.md").write_text("# A\n", encoding="utf-8")
    nested = proj / "vendor" / "nested" / "docs"
    nested.mkdir(parents=True)
    (nested / "ROADMAP.md").write_text("# B\n", encoding="utf-8")

    state = scan_workspace(workspace, lenses_fake, {})
    rels = [r["rel_path"] for r in state.get("roadmaps") or []]

    assert "app/docs/ROADMAP.md" in rels
    assert "app/vendor/nested/docs/ROADMAP.md" in rels
