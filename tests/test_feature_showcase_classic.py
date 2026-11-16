"""Classic feature showcase HTML (scrollytelling stub)."""

from __future__ import annotations

import unittest


class TestFeatureShowcaseClassic(unittest.TestCase):
    def test_body_contains_root_and_five_items(self) -> None:
        from lenses.feature_showcase_classic import FEATURE_SHOWCASE_ITEMS, feature_showcase_body_html

        self.assertEqual(len(FEATURE_SHOWCASE_ITEMS), 5)
        html = feature_showcase_body_html()
        self.assertIn('id="lenses-fs-root"', html)
        self.assertIn("lenses-fs-item-wrap", html)
        self.assertIn("IntersectionObserver", html)
