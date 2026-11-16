"""Tests for async overview telemetry jobs."""

from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from lenses.overview_jobs import (
    get_cached_overview,
    max_overview_workers,
    overview_async_enabled,
    start_overview_job,
    store_cached_overview,
)


class OverviewJobsTests(unittest.TestCase):
    def test_async_enabled_default(self) -> None:
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("LENSES_OVERVIEW_ASYNC", None)
            self.assertTrue(overview_async_enabled())
        with patch.dict(os.environ, {"LENSES_OVERVIEW_ASYNC": "0"}):
            self.assertFalse(overview_async_enabled())

    def test_max_workers_is_three(self) -> None:
        self.assertEqual(max_overview_workers(), 3)

    def test_cache_round_trip(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            payload = {"version": 2, "scope": "overview", "horizon": "week"}
            store_cached_overview(root, horizon_id="week", payload=payload)
            hit = get_cached_overview(root, horizon_id="week")
            self.assertEqual(hit, payload)

    def test_start_job_cache_hit(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            payload = {"version": 2, "scope": "overview", "horizon": "week", "kpi_trends": {}}
            store_cached_overview(root, horizon_id="week", payload=payload)
            state = {"children": [], "workspace_root": str(root)}
            snap = start_overview_job(root, state, horizon="week", force=False)
            self.assertEqual(snap.get("status"), "done")
            self.assertTrue(snap.get("cache_hit"))

    @patch("lenses.overview_jobs.build_overview_chart_payload")
    def test_start_job_queues_compute(self, mock_build) -> None:
        mock_build.return_value = {"version": 2, "scope": "overview"}
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            state = {"children": [{"name": "a", "is_git": True, "path": td}], "workspace_root": td}
            with patch.dict(os.environ, {"LENSES_OVERVIEW_CACHE_SEC": "0"}):
                snap = start_overview_job(root, state, horizon="week", force=True)
            self.assertIn(snap.get("status"), ("queued", "running", "done"))
            self.assertFalse(snap.get("cache_hit"))


if __name__ == "__main__":
    unittest.main()
