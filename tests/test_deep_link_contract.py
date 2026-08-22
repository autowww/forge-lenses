"""Deep-link query contract: parsed URL params match story-hub / plan-spine inputs."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from lenses.forge_spine import build_plan_spine_payload, build_story_hub_payload
from lenses.plan_query import parse_plan_query

WBS = """### Theme: T1

#### Epic: M1E1 — Epic one

| Story ID | Story | Acceptance |
|----------|-------|-------------|
| M1E1S1 | S1 | ok |

#### Tasks

| Task ID | Task | Story |
|---------|------|-------|
| M1E1S1T1 | T1 | M1E1S1 |
"""


class DeepLinkContractTests(unittest.TestCase):
    def test_story_hub_uses_same_ids_as_query_string(self) -> None:
        q = parse_plan_query("repo=myrepo&wbs_p=docs/requirements/WBS.md&id=M1E1S1&roadmap_p=ROADMAP.md")
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            req = root / "docs" / "requirements"
            req.mkdir(parents=True)
            (req / "WBS.md").write_text(WBS, encoding="utf-8")
            (root / "ROADMAP.md").write_text("# R\n", encoding="utf-8")
            p = build_story_hub_payload(
                root,
                repo_hint=q.get("repo", ""),
                wbs_rel=q["wbs_p"],
                work_item_id=q["id"],
                roadmap_rel=q.get("roadmap_p"),
            )
            self.assertTrue(p.get("ok"))
            self.assertEqual(p.get("work_item_id"), "M1E1S1")

    def test_plan_spine_matches_query_repo_and_paths(self) -> None:
        q = parse_plan_query("repo=r&wbs_p=docs/requirements/WBS.md&roadmap_p=ROADMAP.md")
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            base = root / "r"
            req = base / "docs" / "requirements"
            req.mkdir(parents=True)
            (req / "WBS.md").write_text(WBS, encoding="utf-8")
            (base / "ROADMAP.md").write_text("# R\n", encoding="utf-8")
            wbs_rel = str((base / "docs" / "requirements" / "WBS.md").relative_to(root)).replace(
                "\\", "/"
            )
            rm_rel = str((base / "ROADMAP.md").relative_to(root)).replace("\\", "/")
            out = build_plan_spine_payload(
                root,
                repo_hint=q["repo"],
                wbs_rel=wbs_rel,
                roadmap_rel=rm_rel,
            )
            self.assertTrue(out.get("ok"))
            self.assertEqual(out.get("repo_hint"), "r")


if __name__ == "__main__":
    unittest.main()
