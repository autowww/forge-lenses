"""Tests for workspace Forge rollup (Overview)."""

from __future__ import annotations

import unittest
from pathlib import Path

from lenses.overview_forge import build_overview_forge_rollup


class OverviewForgeTests(unittest.TestCase):
    def test_empty_state(self) -> None:
        r = build_overview_forge_rollup(Path("/tmp"), {"wbs": [], "roadmaps": [], "forge_hints": []})
        self.assertTrue(r["ok"])
        self.assertEqual(r["wbs_count"], 0)
        self.assertEqual(r["totals"]["active_sparks"], 0)

    def test_counts_structure(self) -> None:
        r = build_overview_forge_rollup(
            Path("."),
            {
                "wbs": [],
                "roadmaps": [],
                "forge_hints": [],
            },
        )
        self.assertIn("active_sparks", r)
        self.assertIn("horizon_totals", r)
        self.assertIn("upcoming_milestones", r)


if __name__ == "__main__":
    unittest.main()
