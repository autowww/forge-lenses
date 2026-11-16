"""Tests for GET /api/plan-spine payload (single spine: WBS + Charge + roadmap)."""

from __future__ import annotations

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from lenses.forge_spine import build_plan_spine_payload


WBS = """## Themes

### Theme: T1

#### Epic: M1E1 — Epic one

| Story ID | Story | Acceptance |
|----------|-------|-------------|
| M1E1S1 | S1 | ok |

#### Tasks

| Task ID | Task | Story |
|---------|------|-------|
| M1E1S1T1 | T1 | M1E1S1 |
"""

CHARGE = """# Charge

## Active Sparks

| Spark ID | Status |
|----------|--------|
| M1E1S1T1 | open |
"""

ROADMAP = """## Plan

| Status | % complete |
|--------|-------------|
| Active | 50 |
"""


class PlanSpinePayloadTests(unittest.TestCase):
    def test_spine_joins_wbs_charge_roadmap(self) -> None:
        with TemporaryDirectory() as td:
            root = Path(td)
            base = root / "proj"
            req = base / "docs" / "requirements"
            req.mkdir(parents=True)
            wbs_path = req / "WBS.md"
            wbs_path.write_text(WBS, encoding="utf-8")
            ch = base / "forge" / "charge.md"
            ch.parent.mkdir(parents=True, exist_ok=True)
            ch.write_text(CHARGE, encoding="utf-8")
            rm = base / "ROADMAP.md"
            rm.write_text(ROADMAP, encoding="utf-8")
            wbs_rel = str(wbs_path.relative_to(root)).replace("\\", "/")
            rm_rel = str(rm.relative_to(root)).replace("\\", "/")
            out = build_plan_spine_payload(
                root,
                repo_hint="proj",
                wbs_rel=wbs_rel,
                roadmap_rel=rm_rel,
            )
            self.assertTrue(out.get("ok"))
            self.assertEqual(out.get("wbs_rel"), wbs_rel)
            sparks = out.get("charge_sparks") or []
            self.assertTrue(any(r.get("spark_id") == "M1E1S1T1" for r in sparks))
            plan = out.get("plan") or {}
            self.assertIn("M1E1S1", plan.get("story_ids") or [])
            self.assertIn("/wbs/view?p=", out.get("wbs_view", ""))
            forge = out.get("forge") or {}
            self.assertTrue(forge.get("charge_view"))
            rs = out.get("roadmap_summary") or {}
            self.assertTrue(rs.get("metrics") is not None or rs.get("rel_path"))

    def test_spine_missing_wbs(self) -> None:
        with TemporaryDirectory() as td:
            root = Path(td)
            out = build_plan_spine_payload(
                root, repo_hint="", wbs_rel="missing/WBS.md", roadmap_rel=None
            )
            self.assertFalse(out.get("ok"))


if __name__ == "__main__":
    unittest.main()
