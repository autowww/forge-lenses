"""Tests for roadmap Gantt parsing and SVG."""

from __future__ import annotations

import unittest

from lenses.roadmap_charts import roadmap_gantt_html, roadmap_summary_html, svg_roadmap_gantt
from lenses.roadmap_outline import extract_chart_metrics, extract_gantt_model

FIXTURE_MD = """# Test roadmap

### Milestones

| Milestone | Status | Window |
|-----------|--------|--------|
| **M1.1** Alpha | Planned | First |
| **M1.2** Beta | Planned | Second |

### Epics

| Epic ID | Title | Status | Horizon |
|---------|-------|--------|---------|
| **E1** | One | Planned | M1.1 |
| **E2** | Two | Planned | M1.1–M1.2 |
"""


class RoadmapGanttTests(unittest.TestCase):
    def test_extract_gantt_milestones_and_bars(self) -> None:
        m = extract_gantt_model(FIXTURE_MD)
        self.assertTrue(m["has_gantt"])
        self.assertEqual(m["milestones"], ["M1.1", "M1.2"])
        self.assertEqual(len(m["bars"]), 2)
        self.assertEqual(m["bars"][0]["start"], m["bars"][0]["end"])
        self.assertEqual(m["bars"][0]["start"], 0)
        self.assertEqual(m["bars"][1]["start"], 0)
        self.assertEqual(m["bars"][1]["end"], 1)

    def test_svg_roadmap_gantt_contains_labels(self) -> None:
        m = extract_gantt_model(FIXTURE_MD)
        svg = svg_roadmap_gantt(m)
        self.assertIn("<svg", svg)
        self.assertIn("M1.1", svg)
        self.assertTrue("E1" in svg or "One" in svg)

    def test_roadmap_gantt_html_requires_has_gantt(self) -> None:
        m = extract_gantt_model("# Hello\n\nNo tables.\n")
        self.assertEqual(roadmap_gantt_html(m), "")

    def test_roadmap_summary_includes_gantt_when_present(self) -> None:
        m = extract_gantt_model(FIXTURE_MD)
        metrics = extract_chart_metrics(FIXTURE_MD)
        html = roadmap_summary_html(metrics, m)
        self.assertIn("lenses-roadmap-gantt-wrap", html)
        self.assertIn("Timeline (by milestone)", html)

    def test_fallback_milestones_from_epic_horizon_only(self) -> None:
        md = """# X
## Epics
| Epic ID | Horizon |
|---------|---------|
| **A** | M2.2 |
| **B** | M2.1–M2.3 |
"""
        m = extract_gantt_model(md)
        self.assertEqual(m["milestones"], ["M2.1", "M2.2", "M2.3"])
        self.assertTrue(m["has_gantt"])
        self.assertEqual(len(m["bars"]), 2)


if __name__ == "__main__":
    unittest.main()
