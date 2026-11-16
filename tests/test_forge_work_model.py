"""Tests for normalized Forge work graph (milestones, epics, stories, sparks)."""

from __future__ import annotations

import unittest
from pathlib import Path

from lenses.forge_work_model import (
    build_forge_work_model,
    work_model_selectors_payload,
)

WBS_CHAIN = """## Themes

### Theme: T1

#### Epic: M1E1 — Epic one

| Story ID | Story | Dependencies | Priority | Acceptance criteria (summary) |
|----------|-------|--------------|----------|------------------------------|
| M1E1S1 | First story | M1E1S2 | High | Done |
| M1E1S2 | Second story | | | |

#### Tasks

| Task ID | Task | Story | Blockers |
|---------|------|-------|----------|
| M1E1S1T1 | Slice one | M1E1S1 | waiting on review |
"""

WBS_SYNTH_EPIC = """## Themes

### Theme: T1 — no epic heading for M1E2

| Story ID | Story |
|----------|-------|
| M1E2S1 | Story under synthesized epic |
"""

WBS_WITH_MILESTONE_OUTCOME = """## Milestone M1 — Ship v1

Deliver the first vertical slice to production.

#### Epic: M1E1 — Epic one

| Story ID | Story | Dependencies | Priority | Acceptance criteria (summary) |
|----------|-------|--------------|----------|------------------------------|
| M1E1S1 | First story | | | Done |
"""


def _write_min_repo(
    root: Path,
    *,
    wbs_md: str,
    roadmap: str | None = None,
    charge: bool = False,
    ember: bool = False,
    versona: bool = False,
    product: bool = False,
) -> str:
    """Returns wbs_rel relative to root."""
    base = root / "repo"
    req = base / "docs" / "requirements"
    req.mkdir(parents=True)
    wbs_path = req / "WBS.md"
    wbs_path.write_text(wbs_md, encoding="utf-8")
    wbs_rel = str(wbs_path.relative_to(root)).replace("\\", "/")
    if roadmap is not None:
        rp = base / "docs" / "ROADMAP.md"
        rp.parent.mkdir(parents=True, exist_ok=True)
        rp.write_text(roadmap, encoding="utf-8")
    if charge:
        fp = base / "forge" / "charge.md"
        fp.parent.mkdir(parents=True, exist_ok=True)
        fp.write_text(
            "# Charge\n\n## Active Sparks\n\n"
            "| # | Spark ID | Phase | Status |\n|---|----------|-------|--------|\n"
            "| 1 | M1E1S1T1 | x | `done` |\n",
            encoding="utf-8",
        )
    if ember:
        el = base / "ember-logs"
        el.mkdir(parents=True)
        (el / "d.md").write_text(
            "## Decision: Test decision\n\nRefs M1E1S1.\n", encoding="utf-8"
        )
    if versona:
        vr = base / "forge-logs" / "versona" / "2026" / "01"
        vr.mkdir(parents=True)
        (vr / "sess.md").write_text(
            "---\n"
            'session_id: "s1"\n'
            "work_item_refs:\n  - M1E1S1\n---\n\n# S\n",
            encoding="utf-8",
        )
    if product:
        pd = base / "docs" / "product"
        pd.mkdir(parents=True)
        (pd / "overview.md").write_text("# P\n", encoding="utf-8")
    return wbs_rel


class ForgeWorkModelTests(unittest.TestCase):
    def test_milestone_epic_story_spark_chain_and_deps(self) -> None:
        from tempfile import TemporaryDirectory

        with TemporaryDirectory() as td:
            root = Path(td)
            wbs_rel = _write_min_repo(root, wbs_md=WBS_CHAIN)
            m = build_forge_work_model(
                root,
                repo_hint="repo",
                wbs_rel=wbs_rel,
                roadmap_rel=None,
            )
            self.assertTrue(m.sources_present.get("wbs"))
            self.assertIn("M1", m.nodes)
            self.assertIn("M1E1", m.nodes)
            self.assertIn("M1E1S1", m.nodes)
            self.assertIn("M1E1S1T1", m.nodes)
            self.assertEqual(m.nodes["M1E1"].parent_id, "M1")
            self.assertEqual(m.nodes["M1E1S1"].parent_id, "M1E1")
            self.assertEqual(m.nodes["M1E1S1T1"].parent_id, "M1E1S1")
            self.assertEqual(m.nodes["M1E1S1"].dependencies, ["M1E1S2"])
            self.assertEqual(m.nodes["M1E1S1T1"].blockers, ["waiting on review"])
            anc = [x.id for x in m.ancestors("M1E1S1T1")]
            self.assertEqual(anc, ["M1", "M1E1", "M1E1S1"])
            ch = [x.id for x in m.children("M1")]
            self.assertIn("M1E1", ch)

    def test_summary_missing_node(self) -> None:
        from tempfile import TemporaryDirectory

        with TemporaryDirectory() as td:
            root = Path(td)
            wbs_rel = _write_min_repo(root, wbs_md=WBS_CHAIN)
            m = build_forge_work_model(
                root,
                repo_hint="repo",
                wbs_rel=wbs_rel,
                roadmap_rel=None,
            )
            self.assertTrue(m.summary("NO_SUCH_ID").get("missing"))

    def test_missing_optional_sources(self) -> None:
        from tempfile import TemporaryDirectory

        with TemporaryDirectory() as td:
            root = Path(td)
            wbs_rel = _write_min_repo(root, wbs_md=WBS_CHAIN)
            m = build_forge_work_model(
                root,
                repo_hint="repo",
                wbs_rel=wbs_rel,
                roadmap_rel=None,
            )
            self.assertFalse(m.sources_present.get("roadmap"))
            self.assertFalse(m.sources_present.get("charge"))
            self.assertFalse(m.sources_present.get("ember_logs"))
            self.assertFalse(m.sources_present.get("versona"))
            self.assertFalse(m.sources_present.get("product_docs"))
            self.assertIn("M1E1S1", m.nodes)

    def test_milestone_business_outcome_from_wbs_heading(self) -> None:
        from tempfile import TemporaryDirectory

        with TemporaryDirectory() as td:
            root = Path(td)
            wbs_rel = _write_min_repo(root, wbs_md=WBS_WITH_MILESTONE_OUTCOME)
            m = build_forge_work_model(
                root,
                repo_hint="repo",
                wbs_rel=wbs_rel,
                roadmap_rel=None,
            )
            self.assertIn("M1", m.nodes)
            bo = (m.nodes["M1"].extra or {}).get("business_outcome", "")
            self.assertIn("vertical slice", bo)

    def test_provenance_synthesized_epic_story_selectors(self) -> None:
        from tempfile import TemporaryDirectory

        with TemporaryDirectory() as td:
            root = Path(td)
            wbs_rel = _write_min_repo(root, wbs_md=WBS_SYNTH_EPIC)
            m = build_forge_work_model(
                root,
                repo_hint="repo",
                wbs_rel=wbs_rel,
                roadmap_rel=None,
            )
            self.assertTrue(m.nodes["M1E2"].synthesized)
            pl = work_model_selectors_payload(m, "M1E2S1")
            self.assertTrue(pl.get("ok"))
            summ = pl["summary"]
            self.assertFalse(summ.get("missing"))
            prov = summ.get("provenance") or []
            self.assertTrue(
                any(
                    p.get("role") == "wbs" and "WBS.md" in (p.get("path") or "")
                    for p in prov
                )
            )


if __name__ == "__main__":
    unittest.main()
