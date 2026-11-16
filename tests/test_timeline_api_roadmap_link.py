"""Roadmap source links must use /roadmaps/timeline, not /workspace-md (Forge-only allowlist)."""

from __future__ import annotations

from pathlib import Path

from lenses.safe_forge_paths import roadmap_timeline_view_link
from lenses.timeline_api import build_timeline_api_payload


def test_roadmap_timeline_view_link_encodes_path() -> None:
    href = roadmap_timeline_view_link("myproj/docs/ROADMAP.md")
    assert href.startswith("/roadmaps/timeline?")
    assert "p=" in href
    assert "ROADMAP.md" in href


def test_timeline_api_roadmap_source_href(tmp_path: Path) -> None:
    docs = tmp_path / "app" / "docs"
    docs.mkdir(parents=True)
    (docs / "ROADMAP.md").write_text("# R\n\n## M1\n", encoding="utf-8")
    state = {
        "wbs": [
            {"rel_path": "app/docs/requirements/WBS.md", "repo_hint": "app", "kind": "md"},
        ],
        "roadmaps": [{"rel_path": "app/docs/ROADMAP.md", "repo_hint": "app", "kind": "md"}],
    }
    payload = build_timeline_api_payload(
        tmp_path,
        state,
        {"repo": ["app"], "wbs_p": ["app/docs/requirements/WBS.md"], "roadmap_p": ["app/docs/ROADMAP.md"]},
    )
    src = str(payload.get("roadmap_source_href") or "")
    assert src.startswith("/roadmaps/timeline?"), src
    assert "workspace-md" not in src
