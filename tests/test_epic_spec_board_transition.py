"""Transition guards for Spec Flow board POST."""

from __future__ import annotations

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from lenses.epic_spec_board import apply_epic_spec_transition

CHARGE = """---
date: 2026-08-21
---

## Active Epics

| # | id | OpenSpec change | status | actor |
|---|-----|-----------------|--------|-------|
"""

WBS = """#### Epic: M1E5 — Transition epic
"""


class TransitionTests(unittest.TestCase):
    def _tree(self) -> tuple[Path, str, str]:
        tmp = TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        root = Path(tmp.name)
        repo = root / "proj"
        repo.mkdir()
        wbs = repo / "WBS.md"
        wbs.write_text(WBS, encoding="utf-8")
        charge = repo / "forge" / "charge.md"
        charge.parent.mkdir(parents=True)
        charge.write_text(CHARGE, encoding="utf-8")
        (repo / "openspec").mkdir(parents=True, exist_ok=True)
        (repo / "openspec" / "config.yaml").write_text("schema: forge-sdlc\n", encoding="utf-8")
        return root, "proj", "proj/WBS.md"

    def test_ready_to_charged_upserts(self) -> None:
        root, repo_hint, wbs_rel = self._tree()
        repo = root / repo_hint
        change = repo / "openspec" / "changes" / "epic-m1e5"
        change.mkdir(parents=True)
        (change / "proposal.md").write_text("## WBS Epic ID\n\nM1E5\n", encoding="utf-8")
        (change / "specs" / "cap").mkdir(parents=True)
        (change / "specs" / "cap" / "spec.md").write_text("# cap\n", encoding="utf-8")

        with patch("lenses.epic_spec_board._openspec_validate_ok", return_value=True):
            out = apply_epic_spec_transition(
                root,
                repo_hint=repo_hint,
                wbs_rel=wbs_rel,
                epic_id="M1E5",
                to_column="charged",
            )
        self.assertTrue(out.get("ok"), out)
        text = (repo / "forge" / "charge.md").read_text(encoding="utf-8")
        self.assertIn("M1E5", text)
        self.assertIn("planned", text)

    def test_specify_to_ready_without_validate_409(self) -> None:
        root, repo_hint, wbs_rel = self._tree()
        repo = root / repo_hint
        change = repo / "openspec" / "changes" / "epic-m1e5"
        change.mkdir(parents=True)
        (change / "proposal.md").write_text("## WBS Epic ID\n\nM1E5\n", encoding="utf-8")

        with patch("lenses.epic_spec_board._openspec_validate_ok", return_value=False):
            out = apply_epic_spec_transition(
                root,
                repo_hint=repo_hint,
                wbs_rel=wbs_rel,
                epic_id="M1E5",
                to_column="ready",
                change_slug="epic-m1e5",
            )
        self.assertFalse(out.get("ok"))
        self.assertEqual(out.get("error"), "validate_not_green")

    def test_specify_to_ready_wiki_stale_409(self) -> None:
        root, repo_hint, wbs_rel = self._tree()
        repo = root / repo_hint
        change = repo / "openspec" / "changes" / "epic-m1e5"
        change.mkdir(parents=True)
        (change / "proposal.md").write_text(
            "## WBS Epic ID\n\nM1E5\n\n## Dual wiki\n\n"
            "| In-repo path | Handbook shell | Notes |\n"
            "|--------------|----------------|-------|\n"
            "| sdlc/methodologies/forge/SPEC-FLOW-BOARD.md | bpw | |\n",
            encoding="utf-8",
        )
        bp = root / "blueprints" / "sdlc" / "methodologies" / "forge"
        bp.mkdir(parents=True)
        (bp / "SPEC-FLOW-BOARD.md").write_text("# board\n", encoding="utf-8")
        (root / "blueprints-website" / "website").mkdir(parents=True)

        with patch("lenses.epic_spec_board._openspec_validate_ok", return_value=True):
            out = apply_epic_spec_transition(
                root,
                repo_hint=repo_hint,
                wbs_rel=wbs_rel,
                epic_id="M1E5",
                to_column="ready",
                change_slug="epic-m1e5",
            )
        self.assertFalse(out.get("ok"))
        self.assertEqual(out.get("error"), "wiki_stale")

    def test_skip_to_charged_from_intent_forbidden(self) -> None:
        root, repo_hint, wbs_rel = self._tree()
        out = apply_epic_spec_transition(
            root,
            repo_hint=repo_hint,
            wbs_rel=wbs_rel,
            epic_id="M1E5",
            to_column="charged",
        )
        self.assertFalse(out.get("ok"))
        self.assertEqual(out.get("error"), "transition_forbidden")

    def test_charged_to_ready_removes_row(self) -> None:
        root, repo_hint, wbs_rel = self._tree()
        repo = root / repo_hint
        charge = repo / "forge" / "charge.md"
        charge.write_text(
            CHARGE
            + "| 1 | [M1E5](WBS.md) | [epic-m1e5](../openspec/changes/epic-m1e5/) | planned | eng |\n",
            encoding="utf-8",
        )
        out = apply_epic_spec_transition(
            root,
            repo_hint=repo_hint,
            wbs_rel=wbs_rel,
            epic_id="M1E5",
            to_column="ready",
            change_slug="epic-m1e5",
        )
        self.assertTrue(out.get("ok"), out)
        text = charge.read_text(encoding="utf-8")
        self.assertNotIn("| 1 | [M1E5]", text)


if __name__ == "__main__":
    unittest.main()
