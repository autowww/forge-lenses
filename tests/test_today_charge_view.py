"""Tests for Today (Charge) view API and Charge section parsers."""

from __future__ import annotations

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from lenses.charge_semantics import status_banked, status_terminal
from lenses.forge_spine import (
    parse_charge_banking,
    parse_charge_blockers,
    parse_charge_frontmatter,
    parse_charge_sparks,
)
from lenses.today_charge_view import _breadcrumb, build_today_charge_payload
from lenses.forge_work_model import ForgeWorkModel
from lenses.wbs_model import parse_wbs_markdown


SAMPLE_CHARGE = """---
date: 2026-03-30
hat: Alex
iteration: F1
---

# Charge — 2026-03-30

## Active Sparks

| # | Spark ID | Phase | Intent | Status |
|---|----------|-------|--------|--------|
| 1 | M1E1S1T1 | C | Ship widget | in progress |
| 2 | M1E1S1T2 | C | Docs | blocked |
| 3 | M1E1S1T3 | D | QA | done |
| 4 | M1E1S1T4 | C | Later | banked |

## Blockers

| Spark | Blocker | Action |
|-------|---------|--------|
| M1E1S1T2 | API slow | Profile endpoint |

## Banking decisions

| Spark | Reason banked | Restart context |
|-------|---------------|-----------------|
| M1E1S1T4 | Waiting on vendor | Check email |
"""


MIN_WBS = """## Themes

### Theme: T1

#### Epic: M1E1 — Epic one

| Story ID | Story | Acceptance criteria (summary) | Priority |
|----------|-------|--------------------------------|----------|
| M1E1S1 | Story one | | |

#### Tasks

| Task ID | Task | Story | Blockers |
|---------|------|-------|----------|
| M1E1S1T1 | Task one | M1E1S1 | |
| M1E1S1T2 | Task two | M1E1S1 | API slow |
| M1E1S1T3 | Task three | M1E1S1 | |
| M1E1S1T4 | Task four | M1E1S1 | |
"""


class BreadcrumbFallbackTests(unittest.TestCase):
    def test_breadcrumb_when_spark_not_in_work_graph(self) -> None:
        wbs = parse_wbs_markdown("WBS.md", MIN_WBS)
        empty = ForgeWorkModel(repo_hint="r", nodes={}, root_ids=[])
        bc = _breadcrumb(empty, wbs, "M1E1S1T1")
        self.assertGreaterEqual(len(bc), 2)
        self.assertEqual(bc[-1]["kind"], "spark")
        self.assertEqual(bc[-1]["id"], "M1E1S1T1")


class TodayChargeParseTests(unittest.TestCase):
    def test_frontmatter_hat(self) -> None:
        fm = parse_charge_frontmatter(SAMPLE_CHARGE)
        self.assertEqual(fm.get("hat"), "Alex")
        self.assertEqual(fm.get("date"), "2026-03-30")

    def test_blockers_and_banking_tables(self) -> None:
        br = parse_charge_blockers(SAMPLE_CHARGE)
        self.assertEqual(len(br), 1)
        self.assertEqual(br[0]["spark_id"], "M1E1S1T2")
        self.assertIn("Profile", br[0]["action"])
        bk = parse_charge_banking(SAMPLE_CHARGE)
        self.assertEqual(len(bk), 1)
        self.assertEqual(bk[0]["spark_id"], "M1E1S1T4")


class TodayChargeApiTests(unittest.TestCase):
    def test_sections_classification(self) -> None:
        with TemporaryDirectory() as td:
            root = Path(td)
            req = root / "docs" / "requirements"
            req.mkdir(parents=True)
            forge = root / "forge"
            forge.mkdir(parents=True)
            (req / "WBS.md").write_text(MIN_WBS, encoding="utf-8")
            (forge / "charge.md").write_text(SAMPLE_CHARGE, encoding="utf-8")

            payload = build_today_charge_payload(
                root,
                repo_hint="",
                wbs_rel="docs/requirements/WBS.md",
                roadmap_rel=None,
            )
            self.assertTrue(payload.get("ok"))
            sec = payload["sections"]
            active_ids = {r["spark_id"] for r in sec["active"]}
            blocked_ids = {r["spark_id"] for r in sec["blocked"]}
            banked_ids = {r["spark_id"] for r in sec["banked"]}
            resolved_ids = {r["spark_id"] for r in sec["recently_resolved"]}

            self.assertIn("M1E1S1T1", active_ids)
            self.assertIn("M1E1S1T2", blocked_ids)
            self.assertIn("M1E1S1T4", banked_ids)
            self.assertIn("M1E1S1T3", resolved_ids)

            self.assertEqual(payload["charge"].get("hat"), "Alex")
            row_map = {r["spark_id"]: r for r in payload["spark_rows"]}
            self.assertIn("Profile", row_map["M1E1S1T2"]["next_action"])


class ChargeSemanticsTests(unittest.TestCase):
    def test_terminal_and_banked(self) -> None:
        self.assertTrue(status_terminal("done"))
        self.assertTrue(status_banked("banked"))
        self.assertFalse(status_banked("done"))


if __name__ == "__main__":
    unittest.main()
