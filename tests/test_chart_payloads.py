"""Tests for overview chart JSON helpers."""

from __future__ import annotations

import unittest
from datetime import date, timedelta
from pathlib import Path
from unittest.mock import patch

from lenses.chart_payloads import build_overview_chart_payload, horizon_query_days, normalized_horizon_id
from lenses.kpi_history import median_from_prior_six
from lenses.kpi_trends import (
    median_prior_six,
    period_totals_seven_oldest_first,
    trend_tier,
)


class HorizonQueryDaysTests(unittest.TestCase):
    def test_defaults_week(self) -> None:
        self.assertEqual(horizon_query_days(None), 7)
        self.assertEqual(horizon_query_days(""), 7)
        self.assertEqual(horizon_query_days("week"), 7)
        self.assertEqual(horizon_query_days("WEEK"), 7)

    def test_month_quarter(self) -> None:
        self.assertEqual(horizon_query_days("month"), 30)
        self.assertEqual(horizon_query_days("quarter"), 90)

    def test_day(self) -> None:
        self.assertEqual(horizon_query_days("day"), 1)
        self.assertEqual(normalized_horizon_id("day"), "day")

    def test_normalized_horizon_id(self) -> None:
        self.assertEqual(normalized_horizon_id(None), "week")
        self.assertEqual(normalized_horizon_id("month"), "month")
        self.assertEqual(normalized_horizon_id("bogus"), "week")


class KpiTrendsTests(unittest.TestCase):
    def test_median_prior_six(self) -> None:
        # oldest first: p6..p0; median of first six
        pts = [2, 4, 6, 8, 10, 12, 100]
        self.assertEqual(median_prior_six(pts), 7.0)
        self.assertEqual(median_from_prior_six(pts), 7.0)

    def test_period_totals_from_day_map(self) -> None:
        today = date(2026, 4, 1)
        d = 7
        merged: dict[str, int] = {}
        # Fill only current period days with 1 commit each
        for i in range(d):
            dd = today - timedelta(days=i)
            merged[dd.isoformat()] = 1
        totals = period_totals_seven_oldest_first(merged, today, d)
        self.assertEqual(len(totals), 7)
        self.assertEqual(totals[-1], d)
        self.assertEqual(totals[0], 0)

    def test_trend_tier(self) -> None:
        self.assertEqual(trend_tier(10, 5.0), "green")
        self.assertEqual(trend_tier(4, 5.0), "amber")
        self.assertEqual(trend_tier(3, 5.0), "red")
        self.assertEqual(trend_tier(0, 0.0), "amber")
        self.assertEqual(trend_tier(5, 0.0), "green")
        self.assertEqual(trend_tier(5, None), "unknown")


def _fake_overview_repo_row(
    ch: dict,
    *,
    ext_limit: int = 120,
    days: int = 7,
    day_dict: dict | None = None,
) -> tuple:
    name = str(ch.get("name", ""))
    path = Path(str(ch.get("path", "")))
    return (name, path, ch, [], (10, 0), 100, day_dict or {}, ([], 0))


class OverviewPayloadPerRepoLinesTests(unittest.TestCase):
    """`per_repo_lines` mirrors workspace lines loop; mock git I/O."""

    @patch("lenses.chart_payloads.load_kpi_snapshots", return_value=[])
    @patch("lenses.chart_payloads.commits_by_day_dict_range", return_value={})
    @patch("lenses.chart_payloads.git_numstat_between", return_value=(100, 0))
    @patch("lenses.chart_payloads.overview_repo_row_metrics", side_effect=_fake_overview_repo_row)
    def test_per_repo_lines_shape(self, *_args: object) -> None:
        state = {
            "children": [
                {"name": "AlphaRepo", "path": "/tmp/alpha", "is_git": True},
            ],
            "workspace_root": "/tmp",
            "websites": [],
            "wbs": [],
            "roadmaps": [],
        }
        out = build_overview_chart_payload(state, days=7, horizon_id="week")
        pr = out["kpi_trends"]["lines_added"]["per_repo_lines"]
        self.assertIn("AlphaRepo", pr)
        entry = pr["AlphaRepo"]
        self.assertEqual(len(entry["period_totals"]), 7)
        self.assertEqual(entry["period_totals"], [100] * 7)
        self.assertIn("tier", entry)
        self.assertIn("median_prior_6", entry)
        self.assertEqual(entry["median_prior_6"], 100.0)


if __name__ == "__main__":
    unittest.main()
