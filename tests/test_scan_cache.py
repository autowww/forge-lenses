"""Tests for lenses scan cache helpers (stdlib unittest)."""

from __future__ import annotations

import os
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


if __name__ == "__main__":
    unittest.main()
