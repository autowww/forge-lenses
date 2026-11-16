"""Tests for ROADMAP.md epic date patching."""

from __future__ import annotations

import unittest

from lenses.roadmap_date_patch import apply_epic_date_updates

SAMPLE = """# R

## Epics

| Epic ID | Title | Initial start | Initial end | Target start | Target end |
|---------|-------|---------------|-------------|--------------|------------|
| **M1E1** | A | 2026-01-01 | 2026-02-01 | 2026-03-01 | 2026-04-01 |
"""


class RoadmapDatePatchTests(unittest.TestCase):
    def test_patch_target_end(self) -> None:
        new_md, err = apply_epic_date_updates(
            SAMPLE,
            [
                {
                    "epic_id": "M1E1",
                    "target_end": "2026-05-15",
                }
            ],
        )
        self.assertIsNone(err)
        self.assertIn("2026-05-15", new_md)
        self.assertIn("2026-01-01", new_md)

    def test_invalid_date_rejected(self) -> None:
        _new_md, err = apply_epic_date_updates(
            SAMPLE,
            [{"epic_id": "M1E1", "target_start": "not-a-date"}],
        )
        self.assertEqual(err, "invalid_date:target_start")


if __name__ == "__main__":
    unittest.main()
