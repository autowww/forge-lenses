"""Tests for roadmaps matrix aggregation and GET /api/roadmaps-matrix."""

from __future__ import annotations

import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from lenses.roadmaps_matrix_api import (
    aggregate_milestone_rows_for_roadmap,
    build_roadmaps_matrix_payload,
    milestone_norm_key,
)


WBS_TMPL = """## Themes

### Theme: T1

#### Epic: M1E1 — Epic one

| Story ID | Story | Acceptance |
|----------|-------|-------------|
| {sid} | Story {sid} | ok |

#### Tasks

| Task ID | Task | Story |
|---------|------|-------|
| {sid}T1 | Task | {sid} |
"""

ROADMAP_MIN = """## Plan

| Status | % complete |
|--------|-------------|
| Active | 50 |
"""


class RoadmapsMatrixApiTests(unittest.TestCase):
    def test_milestone_norm_key(self) -> None:
        self.assertEqual(
            milestone_norm_key({"epic_key": "E1", "title": "Hello"}),
            milestone_norm_key({"epic_key": "E1", "title": "Hello"}),
        )

    def test_aggregate_merges_two_wbs(self) -> None:
        with TemporaryDirectory() as td:
            root = Path(td)
            for sub in ("a", "b"):
                req = root / "proj" / sub / "docs" / "requirements"
                req.mkdir(parents=True)
                (req / "WBS.md").write_text("# w\n", encoding="utf-8")
            rm_path = root / "proj" / "docs" / "ROADMAP.md"
            rm_path.parent.mkdir(parents=True, exist_ok=True)
            rm_path.write_text(ROADMAP_MIN, encoding="utf-8")
            wbs_a = "proj/a/docs/requirements/WBS.md"
            wbs_b = "proj/b/docs/requirements/WBS.md"
            rm = "proj/docs/ROADMAP.md"

            def fake_spine(_wr: Path, **kwargs: object) -> dict:
                wbs = str(kwargs.get("wbs_rel") or "")
                if wbs == wbs_a:
                    return {
                        "ok": True,
                        "plan": {
                            "milestones": [
                                {
                                    "epic_key": "M1E1",
                                    "title": "Epic one",
                                    "theme": "T1",
                                    "stories": [
                                        {
                                            "id": "M1E1S1",
                                            "title": "A",
                                            "task_count": 1,
                                        }
                                    ],
                                }
                            ]
                        },
                    }
                if wbs == wbs_b:
                    return {
                        "ok": True,
                        "plan": {
                            "milestones": [
                                {
                                    "epic_key": "M1E1",
                                    "title": "Epic one",
                                    "theme": "T1",
                                    "stories": [
                                        {
                                            "id": "M1E1S2",
                                            "title": "B",
                                            "task_count": 0,
                                        }
                                    ],
                                }
                            ]
                        },
                    }
                return {"ok": False}

            rows, pairs, trunc = aggregate_milestone_rows_for_roadmap(
                root,
                repo_hint="proj",
                roadmap_rel=rm,
                wbs_rel_list=[wbs_a, wbs_b],
                epic_to_month={},
                pairs_budget=10,
                spine_fn=fake_spine,
            )
            self.assertFalse(trunc)
            self.assertEqual(pairs, 2)
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0]["unique_story_count"], 2)
            self.assertEqual(rows[0]["wbs_loaded_count"], 2)
            self.assertIn(wbs_a, rows[0]["by_wbs"])

    def test_aggregate_dedupes_same_story_id_across_spines(self) -> None:
        with TemporaryDirectory() as td:
            root = Path(td)
            for sub in ("a", "b"):
                req = root / "proj" / sub / "docs" / "requirements"
                req.mkdir(parents=True)
                (req / "WBS.md").write_text("# w\n", encoding="utf-8")
            rm_path = root / "proj" / "docs" / "ROADMAP.md"
            rm_path.parent.mkdir(parents=True, exist_ok=True)
            rm_path.write_text(ROADMAP_MIN, encoding="utf-8")
            wbs_a = "proj/a/docs/requirements/WBS.md"
            wbs_b = "proj/b/docs/requirements/WBS.md"
            rm = "proj/docs/ROADMAP.md"

            def fake_spine(_wr: Path, **kwargs: object) -> dict:
                return {
                    "ok": True,
                    "plan": {
                        "milestones": [
                            {
                                "epic_key": "M1E1",
                                "title": "Epic one",
                                "theme": "",
                                "stories": [
                                    {"id": "M1E1S1", "title": "Dup", "task_count": 0},
                                ],
                            }
                        ]
                    },
                }

            rows, _, _ = aggregate_milestone_rows_for_roadmap(
                root,
                repo_hint="proj",
                roadmap_rel=rm,
                wbs_rel_list=[wbs_a, wbs_b],
                epic_to_month={},
                pairs_budget=10,
                spine_fn=fake_spine,
            )
            self.assertEqual(rows[0]["unique_story_count"], 1)

    def test_build_unknown_repo_filter(self) -> None:
        state = {
            "wbs": [{"repo_hint": "r1", "rel_path": "r1/docs/requirements/WBS.md", "kind": "md"}],
            "roadmaps": [],
        }
        out = build_roadmaps_matrix_payload(
            Path("/tmp/ws"), state, repo_filter="nope"
        )
        self.assertFalse(out.get("ok"))
        self.assertEqual(out.get("error"), "unknown_repo_filter")

    def test_integration_two_wbs_one_roadmap(self) -> None:
        with TemporaryDirectory() as td:
            root = Path(td)
            base = root / "proj"
            for sub, sid in (("a", "M1E1S1"), ("b", "M1E1S2")):
                req = base / sub / "docs" / "requirements"
                req.mkdir(parents=True)
                (req / "WBS.md").write_text(
                    WBS_TMPL.format(sid=sid), encoding="utf-8"
                )
            docs = base / "docs"
            docs.mkdir(parents=True)
            (docs / "ROADMAP.md").write_text(ROADMAP_MIN, encoding="utf-8")
            ch = base / "forge" / "charge.md"
            ch.parent.mkdir(parents=True, exist_ok=True)
            ch.write_text(
                "# Charge\n\n## Active Sparks\n\n| Spark ID | Status |\n|----------|--------|\n",
                encoding="utf-8",
            )

            wbs_a = "proj/a/docs/requirements/WBS.md"
            wbs_b = "proj/b/docs/requirements/WBS.md"
            rm_rel = "proj/docs/ROADMAP.md"

            state = {
                "wbs": [
                    {"repo_hint": "proj", "rel_path": wbs_a, "kind": "md"},
                    {"repo_hint": "proj", "rel_path": wbs_b, "kind": "md"},
                ],
                "roadmaps": [
                    {"repo_hint": "proj", "rel_path": rm_rel, "kind": "md"},
                ],
            }
            out = build_roadmaps_matrix_payload(root, state, repo_filter="all")
            self.assertTrue(out.get("ok"), msg=out)
            rms = out.get("roadmaps") or []
            self.assertEqual(len(rms), 1)
            ms = rms[0].get("milestones") or []
            self.assertTrue(len(ms) >= 1)
            self.assertGreaterEqual(ms[0].get("wbs_loaded_count", 0), 1)

    def test_payload_json_roundtrip(self) -> None:
        fake_state: dict = {"wbs": [], "roadmaps": []}
        out = build_roadmaps_matrix_payload(
            Path("/tmp"), fake_state, repo_filter="all"
        )
        data = json.loads(json.dumps(out))
        self.assertIn("ok", data)
