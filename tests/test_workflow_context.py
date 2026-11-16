"""Tests for GET /api/workflow-context payload builder."""

from __future__ import annotations

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from lenses.charge_semantics import charge_active_today_count
from lenses.workflow_context import build_workflow_context_payload


class WorkflowContextTests(unittest.TestCase):
    def test_charge_today_excludes_done(self) -> None:
        rows = [
            {"spark_id": "A", "status": "done"},
            {"spark_id": "B", "status": "in progress"},
            {"spark_id": "C", "status": ""},
        ]
        self.assertEqual(charge_active_today_count(rows), 2)

    def test_context_payload_shape(self) -> None:
        wbs = """## Themes

### Theme: T1

#### Epic: M1E1 — E1

| Story ID | Story | Acceptance criteria (summary) | Priority |
|----------|-------|--------------------------------|----------|
| M1E1S1 | S1 | | |

#### Tasks

| Task ID | Task | Story | Blockers |
|---------|------|-------|----------|
| M1E1S1T1 | T1 | M1E1S1 | waiting |
"""
        with TemporaryDirectory() as td:
            root = Path(td)
            base = root / "repo"
            req = base / "docs" / "requirements"
            req.mkdir(parents=True)
            wbs_path = req / "WBS.md"
            wbs_path.write_text(wbs, encoding="utf-8")
            wbs_rel = str(wbs_path.relative_to(root)).replace("\\", "/")
            ch = base / "forge" / "charge.md"
            ch.parent.mkdir(parents=True, exist_ok=True)
            ch.write_text(
                "# Charge\n\n## Active Sparks\n\n"
                "| Spark ID | Status |\n|----------|--------|\n"
                "| M1E1S1T1 | open |\n",
                encoding="utf-8",
            )
            out = build_workflow_context_payload(
                root, repo_hint="repo", wbs_rel=wbs_rel, roadmap_rel=None
            )
            self.assertTrue(out.get("ok"))
            ctx = out.get("context") or {}
            self.assertIn("blocked_count", ctx)
            self.assertGreaterEqual(ctx["blocked_count"], 1)
            self.assertIn("charge_today_size", ctx)
            self.assertGreaterEqual(ctx["charge_today_size"], 1)
            self.assertIn("pending_decisions_count", ctx)
            self.assertIn("sources_present", ctx)

    def test_missing_wbs(self) -> None:
        with TemporaryDirectory() as td:
            root = Path(td)
            out = build_workflow_context_payload(
                root, repo_hint="", wbs_rel="nope.md", roadmap_rel=None
            )
            self.assertFalse(out.get("ok"))


if __name__ == "__main__":
    unittest.main()
