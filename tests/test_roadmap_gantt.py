"""Tests for roadmap Gantt parsing and SVG."""

from __future__ import annotations

import unittest

from lenses.roadmap_charts import (
    roadmap_date_shift_html,
    roadmap_gantt_html,
    roadmap_summary_html,
    svg_roadmap_date_shift,
    svg_roadmap_gantt,
)
from lenses.roadmap_outline import (
    extract_chart_metrics,
    extract_date_shift_model,
    extract_gantt_model,
)

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

FIXTURE_MD_DATES = """# Test roadmap dates

## Epics with dates

| Epic ID | Title | Status | Initial start | Initial end | Target start | Target end |
|---------|-------|--------|---------------|-------------|--------------|------------|
| **E1** | Alpha | Planned | 2026-01-01 | 2026-03-01 | 2026-02-01 | 2026-04-01 |
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

    def test_roadmap_summary_no_ks_when_disabled(self) -> None:
        metrics = extract_chart_metrics(FIXTURE_MD)
        html = roadmap_summary_html(metrics, {}, include_ks_diagrams=False)
        self.assertNotIn("__ks/assets/svg/template-timeline.svg", html)
        self.assertNotIn("__ks/assets/svg/template-roadmap.svg", html)

    def test_epic_id_on_bar_when_epic_column_has_forge_id(self) -> None:
        md = """# T
### Milestones
| Milestone | Status |
|-----------|--------|
| **M1.1** | ok |
### Epics
| Epic ID | Title | Horizon |
|---------|-------|---------|
| **M1E1** | One | M1.1 |
"""
        m = extract_gantt_model(md)
        self.assertTrue(m["has_gantt"])
        self.assertEqual(m["bars"][0].get("epic_id"), "M1E1")
        svg = svg_roadmap_gantt(m)
        self.assertIn("data-lenses-node-id", svg)
        self.assertIn("M1E1", svg)

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

    def test_extract_date_shift_rows(self) -> None:
        ds = extract_date_shift_model(FIXTURE_MD_DATES)
        self.assertTrue(ds["has_date_shift"])
        rows = ds["rows"]
        self.assertEqual(len(rows), 1)
        r0 = rows[0]
        self.assertEqual(r0.get("initial_start"), "2026-01-01")
        self.assertEqual(r0.get("initial_end"), "2026-03-01")
        self.assertEqual(r0.get("target_start"), "2026-02-01")
        self.assertEqual(r0.get("target_end"), "2026-04-01")

    def test_svg_date_shift_and_summary(self) -> None:
        ds = extract_date_shift_model(FIXTURE_MD_DATES)
        svg = svg_roadmap_date_shift(ds)
        self.assertIn("<svg", svg)
        self.assertIn("2026-01-01", svg)
        self.assertIn("Initial", svg)
        html = roadmap_date_shift_html(ds)
        self.assertIn("lenses-roadmap-dateshift-wrap", html)
        metrics = extract_chart_metrics(FIXTURE_MD_DATES)
        out = roadmap_summary_html(metrics, {}, ds)
        self.assertIn("lenses-roadmap-dateshift-wrap", out)


if __name__ == "__main__":
    unittest.main()
