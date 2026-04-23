"""Snapshot-style tests for /plan HTML markup hooks."""

from __future__ import annotations

import unittest
from pathlib import Path

from lenses.render import page_plan, page_timeline


class PlanPageHtmlTests(unittest.TestCase):
    def test_rail_toggle_and_explorer_hooks(self) -> None:
        html = page_plan(
            {"wbs": [], "roadmaps": []},
            "https://blueprints.example/handbook",
            "https://forge.example",
            Path("/tmp"),
        )
        self.assertIn('id="lenses-plan-rail-toggle"', html)
        self.assertIn('id="lenses-plan-explorer-row"', html)
        self.assertIn("lenses-plan-rail-collapsed", html)
        self.assertIn('role="tablist"', html)
        self.assertIn("lenses-plan-glossary", html)

    def test_repository_select_includes_roadmap_only_repo(self) -> None:
        html = page_plan(
            {
                "wbs": [],
                "roadmaps": [
                    {
                        "repo_hint": "solo",
                        "rel_path": "solo/docs/ROADMAP.md",
                        "kind": "md",
                    },
                ],
            },
            "https://blueprints.example/handbook",
            "https://forge.example",
            Path("/tmp"),
        )
        self.assertIn('id="lenses-plan-repo"', html)
        self.assertIn('<option value="solo">solo</option>', html)

    def test_timeline_repository_select_includes_roadmap_only_repo(self) -> None:
        html = page_timeline(
            {
                "wbs": [],
                "roadmaps": [
                    {
                        "repo_hint": "solo",
                        "rel_path": "solo/docs/ROADMAP.md",
                        "kind": "md",
                    },
                ],
                "workspace_root": "/tmp",
            },
            "https://blueprints.example/handbook",
            "https://forge.example",
            Path("/tmp"),
            {},
        )
        self.assertIn('id="lenses-timeline-repo"', html)
        self.assertIn('<option value="solo"', html)
        self.assertIn(">solo</option>", html)

    def test_plan_sidebar_preserves_repo_scope_in_nav_links(self) -> None:
        html = page_plan(
            {
                "children": [{"name": "Situ8"}],
                "wbs": [],
                "roadmaps": [],
            },
            "https://blueprints.example/handbook",
            "https://forge.example",
            Path("/tmp"),
            {"repo": ["Situ8"]},
        )
        self.assertIn('href="/plan?repo=Situ8"', html)
        self.assertIn('href="/timeline?repo=Situ8"', html)
        self.assertIn('>Situ8</option>', html)


if __name__ == "__main__":
    unittest.main()
