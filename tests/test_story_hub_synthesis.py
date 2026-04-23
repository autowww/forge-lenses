"""Tests for story definition synthesis and story-hub payload shape."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from lenses.forge_spine import build_story_hub_payload
from lenses.story_definition_synthesis import (
    build_story_view_dict,
    roadmap_hits_for_story,
    synthesize_wbs_slots,
)
from lenses.wbs_model import parse_wbs_markdown

WBS_MINIMAL = """### Theme: T1

#### Epic: M1E1 — Epic one

| Story ID | Story | Problem | Acceptance criteria (summary) |
|----------|-------|---------|------------------------------|
| M1E1S1 | First | We lack X | User sees Y |

#### Tasks

| Task ID | Task | Story | Phase |
|---------|------|-------|-------|
| M1E1S1T1 | Slice | M1E1S1 | build |
"""

WBS_MULTI_COL = """### Theme: T1

#### Epic: M1E1 — Epic one

| Story ID | Story | Problem | Issue |
|----------|-------|---------|-------|
| M1E1S1 | First | Alpha | Beta |

#### Tasks

| Task ID | Task | Story |
|---------|------|-------|
| M1E1S1T1 | Slice | M1E1S1 |
"""


class StoryHubSynthesisTests(unittest.TestCase):
    def test_synthesize_wbs_slots_problem_acceptance(self) -> None:
        m = parse_wbs_markdown("docs/requirements/WBS.md", WBS_MINIMAL)
        st = m.stories["M1E1S1"]
        slots, _ = synthesize_wbs_slots(st, "docs/requirements/WBS.md")
        self.assertIn("problem", slots)
        self.assertIn("We lack X", slots["problem"]["text"])
        self.assertIn("acceptance", slots)
        self.assertIn("User sees Y", slots["acceptance"]["text"])

    def test_phase_affinity_in_story_view(self) -> None:
        m = parse_wbs_markdown("docs/requirements/WBS.md", WBS_MINIMAL)
        st = m.stories["M1E1S1"]
        sv = build_story_view_dict(
            st,
            m,
            "docs/requirements/WBS.md",
            None,
            None,
            work_item_id="M1E1S1",
        )
        self.assertEqual(sv["phase_affinity"], ["build"])

    def test_roadmap_hits_contain_section(self) -> None:
        md = "## Roadmap\n\n### Story M1E1S1 scope\n\nDetails here.\n"
        hits = roadmap_hits_for_story("ROADMAP.md", md, "M1E1S1")
        self.assertTrue(len(hits) >= 1)
        self.assertIn("section_id", hits[0])
        self.assertIn("/roadmaps/preview?", hits[0]["preview_href"])
        self.assertIn("p=", hits[0]["preview_href"])

    def test_build_story_hub_payload_story_view_keys(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            req = root / "docs" / "requirements"
            req.mkdir(parents=True)
            wbs_path = req / "WBS.md"
            wbs_path.write_text(WBS_MINIMAL, encoding="utf-8")
            rm = root / "ROADMAP.md"
            rm.write_text(
                "## Plan\n\n### Track M1E1S1\n\nRoadmap notes for the story.\n",
                encoding="utf-8",
            )
            p = build_story_hub_payload(
                root,
                repo_hint="",
                wbs_rel="docs/requirements/WBS.md",
                work_item_id="M1E1S1",
                roadmap_rel="ROADMAP.md",
            )
            self.assertTrue(p.get("ok"))
            sv = p.get("story_view")
            self.assertIsNotNone(sv)
            assert sv is not None
            self.assertIn("slots", sv)
            self.assertIn("product_context", sv)
            self.assertIn("decisions", sv)
            self.assertIn("execution", sv)
            self.assertIn("sources", sv)
            self.assertIn("roadmap_ctx", p)
            ex = sv["execution"]
            self.assertIn("sparks", ex)
            self.assertIn("charge_rows", ex)
            self.assertTrue(sv.get("roadmap_hits"))

    def test_multi_column_merges_into_same_slot(self) -> None:
        m = parse_wbs_markdown("docs/requirements/WBS.md", WBS_MULTI_COL)
        st = m.stories["M1E1S1"]
        slots, _ = synthesize_wbs_slots(st, "docs/requirements/WBS.md")
        self.assertIn("problem", slots)
        self.assertIn("Alpha", slots["problem"]["text"])
        self.assertIn("Beta", slots["problem"]["text"])
        self.assertGreaterEqual(len(slots["problem"].get("sources") or []), 2)

    def test_story_hub_without_charge_file(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            req = root / "docs" / "requirements"
            req.mkdir(parents=True)
            wbs_path = req / "WBS.md"
            wbs_path.write_text(WBS_MINIMAL, encoding="utf-8")
            p = build_story_hub_payload(
                root,
                repo_hint="",
                wbs_rel="docs/requirements/WBS.md",
                work_item_id="M1E1S1",
                roadmap_rel=None,
            )
            self.assertTrue(p.get("ok"))
            sv = p.get("story_view")
            self.assertIsNotNone(sv)
            assert sv is not None
            src = sv.get("sources") or {}
            self.assertEqual(src.get("charge"), "")
            ex = sv.get("execution") or {}
            self.assertEqual(ex.get("charge_rows"), [])

    def test_charge_rows_align_with_spark_selection(self) -> None:
        charge_md = """# Charge

## Active Sparks

| Spark ID | Status |
|----------|--------|
| M1E1S1T1 | in-progress |
"""
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            req = root / "docs" / "requirements"
            req.mkdir(parents=True)
            wbs_path = req / "WBS.md"
            wbs_path.write_text(WBS_MINIMAL, encoding="utf-8")
            ch = root / "forge" / "charge.md"
            ch.parent.mkdir(parents=True, exist_ok=True)
            ch.write_text(charge_md, encoding="utf-8")
            p = build_story_hub_payload(
                root,
                repo_hint="",
                wbs_rel="docs/requirements/WBS.md",
                work_item_id="M1E1S1T1",
                roadmap_rel=None,
            )
            self.assertTrue(p.get("ok"))
            sv = p.get("story_view")
            self.assertIsNotNone(sv)
            assert sv is not None
            ex = sv.get("execution") or {}
            rows = ex.get("charge_rows") or []
            self.assertTrue(any(r.get("spark_id") == "M1E1S1T1" for r in rows))
            src = sv.get("sources") or {}
            self.assertTrue(src.get("charge"))


if __name__ == "__main__":
    unittest.main()
