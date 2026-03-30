"""Tests for lenses scan cache helpers (stdlib unittest)."""

from __future__ import annotations

import os
from pathlib import Path
import unittest
from unittest.mock import patch

# Run from repo root: PYTHONPATH=. python3 -m unittest discover -s tests -v


class TestScanCacheHelpers(unittest.TestCase):
    def test_refresh_query_truthy(self) -> None:
        from lenses.serve import _refresh_query_truthy

        self.assertFalse(_refresh_query_truthy({}))
        self.assertFalse(_refresh_query_truthy({"refresh": ["0"]}))
        self.assertTrue(_refresh_query_truthy({"refresh": ["1"]}))
        self.assertTrue(_refresh_query_truthy({"refresh": ["true"]}))
        self.assertTrue(_refresh_query_truthy({"refresh": ["yes"]}))

    def test_scan_cache_ttl_sec_default(self) -> None:
        from lenses.serve import _DEFAULT_SCAN_CACHE_SEC, _scan_cache_ttl_sec

        with patch.dict(os.environ, {}, clear=True):
            t = _scan_cache_ttl_sec()
            self.assertEqual(t, _DEFAULT_SCAN_CACHE_SEC)

    def test_scan_cache_ttl_sec_disabled(self) -> None:
        from lenses.serve import _scan_cache_ttl_sec

        with patch.dict(os.environ, {"LENSES_SCAN_CACHE_SEC": "0"}):
            self.assertIsNone(_scan_cache_ttl_sec())

    def test_scan_cache_ttl_sec_custom(self) -> None:
        from lenses.serve import _scan_cache_ttl_sec

        with patch.dict(os.environ, {"LENSES_SCAN_CACHE_SEC": "10"}):
            self.assertEqual(_scan_cache_ttl_sec(), 10.0)

    def test_scan_force_refresh_bypasses_cache(self) -> None:
        """Second _scan without force_refresh hits cache; force_refresh=True re-runs scan_workspace."""
        from lenses.serve import LensesHandler, _scan_cache_store

        fake_state = {
            "workspace_root": "/tmp/ws",
            "children": [],
            "lenses_repo_root": "/tmp/lenses",
            "resolved_at": "",
        }
        calls: list[int] = []

        def fake_scan(*_a, **_k):
            calls.append(1)
            return dict(fake_state)

        def fake_enrich(_state, _reg):
            return None

        with patch.dict(os.environ, {"LENSES_SCAN_CACHE_SEC": "300"}):
            with patch("lenses.serve.scan_workspace", side_effect=fake_scan):
                with patch(
                    "lenses.serve.enrich_workspace_with_standards", side_effect=fake_enrich
                ):
                    _scan_cache_store.clear()

                    class _Dummy:
                        workspace_root = Path("/tmp/ws")
                        registry: dict = {}

                    d = _Dummy()
                    LensesHandler._scan(d, git_extended=False, force_refresh=False)
                    LensesHandler._scan(d, git_extended=False, force_refresh=False)
                    self.assertEqual(len(calls), 1)
                    LensesHandler._scan(d, git_extended=False, force_refresh=True)
                    self.assertEqual(len(calls), 2)


if __name__ == "__main__":
    unittest.main()
