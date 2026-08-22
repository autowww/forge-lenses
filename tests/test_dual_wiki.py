"""Tests for dual wiki parse, freshness, and refresh script policy."""

from __future__ import annotations

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from lenses.dual_wiki import freshness, parse_dual_wiki_surfaces

EXPLICIT = """## Dual wiki

| In-repo path | Handbook shell | Notes |
|--------------|----------------|-------|
| sdlc/methodologies/forge/SPEC-FLOW-BOARD.md | bpw | canon |
"""

EMPTY_SECTION = """## Dual wiki

| In-repo path | Handbook shell | Notes |
|--------------|----------------|-------|
"""

MISSING = """## Why

No dual wiki here.
"""


class ParseDualWikiTests(unittest.TestCase):
    def test_explicit_table(self) -> None:
        sides = parse_dual_wiki_surfaces(EXPLICIT)
        self.assertEqual(len(sides), 1)
        self.assertIn("SPEC-FLOW-BOARD", sides[0]["in_repo"])
        self.assertEqual(sides[0]["handbook_shell"], "bpw")

    def test_empty_defaults_methodology(self) -> None:
        sides = parse_dual_wiki_surfaces(EMPTY_SECTION)
        self.assertTrue(sides)
        self.assertEqual(sides[0]["handbook_shell"], "bpw")

    def test_missing_heading_defaults_lenses(self) -> None:
        sides = parse_dual_wiki_surfaces(MISSING, repo_hint="forge-lenses")
        self.assertTrue(sides)
        self.assertEqual(sides[0]["handbook_shell"], "flsw")


class FreshnessTests(unittest.TestCase):
    def test_stale_missing_html(self) -> None:
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            bp = root / "blueprints"
            bpw = root / "blueprints-website" / "website"
            bp.mkdir()
            bpw.mkdir(parents=True)
            src = bp / "sdlc" / "methodologies" / "forge" / "SPEC-FLOW-BOARD.md"
            src.parent.mkdir(parents=True)
            src.write_text("# board\n", encoding="utf-8")
            repo = root / "proj"
            repo.mkdir()
            fr = freshness(
                root,
                repo_base=repo,
                proposal_md=EXPLICIT,
                repo_hint="proj",
            )
        self.assertTrue(fr["stale"])
        self.assertIn("handbook HTML", " ".join(fr.get("reasons") or []))

    def test_skip_absent_shell(self) -> None:
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            repo = root / "proj"
            repo.mkdir()
            proposal = """## Dual wiki

| In-repo path | Handbook shell | Notes |
|--------------|----------------|-------|
| docs/foo.md | none | skip |
"""
            fr = freshness(root, repo_base=repo, proposal_md=proposal)
            self.assertFalse(fr["stale"])
            self.assertTrue(fr["sides"][0].get("skipped"))


class RefreshScriptPolicyTests(unittest.TestCase):
    def test_refresh_script_rejects_deploy(self) -> None:
        candidates = [
            Path(__file__).resolve().parents[2] / "scripts" / "refresh-dual-wiki.sh",
            Path.home() / "Code" / "scripts" / "refresh-dual-wiki.sh",
        ]
        script = next((p for p in candidates if p.is_file()), None)
        self.assertIsNotNone(script, "refresh-dual-wiki.sh missing")
        text = script.read_text(encoding="utf-8")
        self.assertNotIn("deploy-websites", text)
        self.assertIn("dry-run", text)


if __name__ == "__main__":
    unittest.main()
