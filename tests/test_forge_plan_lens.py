"""Tests for WBS model, Charge parsing, safe Forge paths, and spine helpers."""

from __future__ import annotations

import unittest
from pathlib import Path
import tempfile

from lenses.forge_spine import (
    index_versona_sessions,
    parse_charge_sparks,
    sessions_for_id,
    wbs_model_to_plan_tree,
)
from lenses.safe_forge_paths import safe_forge_workspace_file
from lenses.wbs_model import parse_wbs_markdown

WBS_FIXTURE = """## 2. Themes

### Theme: T1 — Test

#### Epic: M1E1 — Epic one

| Story ID | Story | Acceptance criteria (summary) | Priority |
|----------|-------|------------------------------|----------|
| M1E1S1 | First story | `docs/a.md` | High |

#### Tasks

| Task ID | Task | Story |
|---------|------|-------|
| M1E1S1T1 | Slice one | M1E1S1 |
"""

CHARGE_FIXTURE = """# Charge

## Active Sparks

| # | Spark ID | Phase | Intent | Status |
|---|----------|-------|--------|--------|
| 1 | M1E1S1T1 | specify: | Do it | `in-progress` |
"""

VERSONA_FIXTURE = """---
session_id: "sess-1"
started_at: "2026-01-01T12:00:00Z"
work_item_refs:
  - M1E1S1
work_item_kind: spark
---

# Session
"""


class ForgePlanLensTests(unittest.TestCase):
    def test_parse_wbs_story_and_task(self) -> None:
        m = parse_wbs_markdown("x/WBS.md", WBS_FIXTURE)
        self.assertIn("M1E1S1", m.stories)
        self.assertEqual(m.stories["M1E1S1"].title, "First story")
        self.assertIn("docs/a.md", m.stories["M1E1S1"].product_paths)
        self.assertEqual(m.stories["M1E1S1"].priority, "High")
        self.assertIn("M1E1S1T1", m.tasks)
        self.assertEqual(m.tasks["M1E1S1T1"].story_id, "M1E1S1")

    def test_wbs_model_to_plan_tree(self) -> None:
        m = parse_wbs_markdown("x/WBS.md", WBS_FIXTURE)
        tree = wbs_model_to_plan_tree(m)
        self.assertTrue(tree["milestones"])
        self.assertTrue(tree["story_ids"])

    def test_parse_charge(self) -> None:
        rows = parse_charge_sparks(CHARGE_FIXTURE)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["spark_id"], "M1E1S1T1")
        self.assertIn("in-progress", rows[0]["status"])

    def test_safe_forge_workspace_file(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            good = root / "proj" / "forge" / "charge.md"
            good.parent.mkdir(parents=True)
            good.write_text("# x", encoding="utf-8")
            rel = "proj/forge/charge.md"
            sp = safe_forge_workspace_file(root, rel)
            self.assertIsNotNone(sp)
            bad = root / "proj" / "forge" / "other.md"
            bad.write_text("# y", encoding="utf-8")
            self.assertIsNone(safe_forge_workspace_file(root, "proj/forge/other.md"))

    def test_versona_index(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            sess = root / "r" / "forge-logs" / "versona" / "pm" / "s1" / "session.md"
            sess.parent.mkdir(parents=True)
            sess.write_text(VERSONA_FIXTURE, encoding="utf-8")
            vs = index_versona_sessions(root, root / "r" / "forge-logs" / "versona")
            self.assertEqual(len(vs), 1)
            hit = sessions_for_id(vs, "M1E1S1")
            self.assertEqual(len(hit), 1)


if __name__ == "__main__":
    unittest.main()
