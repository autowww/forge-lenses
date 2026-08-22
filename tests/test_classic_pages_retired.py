"""Classic dashboard HTML builders were removed after Studio UX5 soak."""

from __future__ import annotations

import unittest

from lenses import render


class ClassicPagesRetiredTests(unittest.TestCase):
    RETIRED = (
        "page_overview",
        "page_projects",
        "page_tutorials",
        "page_project_detail",
        "page_search",
        "page_sticker_board_hub",
        "page_websites",
        "page_websites_browse",
        "page_wbs",
        "page_timeline",
        "page_plan",
    )

    def test_classic_dashboard_pages_removed(self) -> None:
        for name in self.RETIRED:
            with self.subTest(name=name):
                self.assertFalse(hasattr(render, name), f"{name} should be removed from lenses.render")

    def test_embed_and_tooling_pages_remain(self) -> None:
        for name in (
            "page_view_embed",
            "page_wbs_view",
            "page_sticker_board_editor",
            "page_toolset",
            "page_toolset_run",
        ):
            with self.subTest(name=name):
                self.assertTrue(hasattr(render, name), f"{name} should remain in lenses.render")


if __name__ == "__main__":
    unittest.main()
