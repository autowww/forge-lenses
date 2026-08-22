"""Tests for Spec Flow board derivation and APIs."""

from __future__ import annotations

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from lenses.charge_mutate import upsert_epic_on_charge
from lenses.epic_spec_board import (
    SPEC_FLOW_COLUMNS,
    build_epic_spec_board_payload,
    derive_column,
    detect_execution_profile,
    match_change_to_epic,
    scan_openspec_changes,
)
from lenses.forge_spine import parse_charge_epics

SAMPLE_EPIC_CHARGE = """---
date: 2026-08-21
hat: engineering
---

# Charge

## Active Epics

| # | id | OpenSpec change | status | actor |
|---|-----|-----------------|--------|-------|
| 1 | [M1E3](docs/WBS.md) | [adopt](../openspec/changes/adopt/) | in progress | eng |
"""

MIN_WBS = """#### Epic: M1E3 — Pilot epic

| Story ID | Story | Acceptance criteria (summary) | Priority |
|----------|-------|--------------------------------|----------|
| M1E3S1 | Story | | |
"""


class ParseChargeEpicsTests(unittest.TestCase):
    def test_parse_active_epics(self) -> None:
        rows = parse_charge_epics(SAMPLE_EPIC_CHARGE)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["epic_id"], "M1E3")
        self.assertEqual(rows[0]["change_slug"], "adopt")
        self.assertEqual(rows[0]["status"], "in progress")
        self.assertEqual(rows[0]["actor"], "eng")


class DeriveColumnTests(unittest.TestCase):
    def test_intent_without_change(self) -> None:
        col = derive_column(
            epic_id="M1E9",
            change_slug=None,
            changes={},
            charge_by_epic={},
        )
        self.assertEqual(col, "intent")

    def test_specify_without_validate(self) -> None:
        col = derive_column(
            epic_id="M1E3",
            change_slug="adopt",
            changes={"adopt": {"validate_ok": False, "archived": False}},
            charge_by_epic={},
        )
        self.assertEqual(col, "specify")

    def test_ready_when_validate_green(self) -> None:
        col = derive_column(
            epic_id="M1E3",
            change_slug="adopt",
            changes={"adopt": {"validate_ok": True, "archived": False}},
            charge_by_epic={},
        )
        self.assertEqual(col, "ready")

    def test_charged_planned(self) -> None:
        col = derive_column(
            epic_id="M1E3",
            change_slug="adopt",
            changes={"adopt": {"validate_ok": True, "archived": False}},
            charge_by_epic={"M1E3": {"status": "planned"}},
        )
        self.assertEqual(col, "charged")

    def test_apply_in_progress(self) -> None:
        col = derive_column(
            epic_id="M1E3",
            change_slug="adopt",
            changes={"adopt": {"validate_ok": True, "archived": False}},
            charge_by_epic={"M1E3": {"status": "in progress"}},
        )
        self.assertEqual(col, "apply")

    def test_verify_done(self) -> None:
        col = derive_column(
            epic_id="M1E3",
            change_slug="adopt",
            changes={"adopt": {"validate_ok": True, "archived": False}},
            charge_by_epic={"M1E3": {"status": "done"}},
        )
        self.assertEqual(col, "verify")

    def test_archived(self) -> None:
        col = derive_column(
            epic_id="M1E3",
            change_slug="adopt",
            changes={"adopt": {"validate_ok": True, "archived": True, "proposal_epic_id": "M1E3"}},
            charge_by_epic={},
        )
        self.assertEqual(col, "archived")

    def test_all_columns_in_enum(self) -> None:
        for c in ("intent", "specify", "ready", "charged", "apply", "verify", "archived"):
            self.assertIn(c, SPEC_FLOW_COLUMNS)


class EpicSpecBoardPayloadTests(unittest.TestCase):
    def test_fixture_tree_columns(self) -> None:
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            repo = root / "fl"
            repo.mkdir()
            wbs = repo / "docs" / "WBS.md"
            wbs.parent.mkdir(parents=True)
            wbs.write_text(MIN_WBS, encoding="utf-8")
            charge = repo / "forge" / "charge.md"
            charge.parent.mkdir(parents=True)
            charge.write_text(SAMPLE_EPIC_CHARGE, encoding="utf-8")
            change = repo / "openspec" / "changes" / "adopt"
            change.mkdir(parents=True)
            (change / "proposal.md").write_text("## WBS Epic ID\n\nM1E3\n", encoding="utf-8")
            (repo / "openspec" / "config.yaml").write_text("schema: forge-sdlc\n", encoding="utf-8")

            payload = build_epic_spec_board_payload(
                root,
                repo_hint="fl",
                wbs_rel="fl/docs/WBS.md",
            )
            self.assertTrue(payload.get("ok"))
            self.assertEqual(payload.get("profile"), "epic")
            cards = payload.get("cards") or []
            self.assertGreaterEqual(len(cards), 1)
            m1e3 = next(c for c in cards if c["epic_id"] == "M1E3")
            self.assertEqual(m1e3["column"], "apply")

    def test_spark_profile_empty_cards(self) -> None:
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            repo = root / "r"
            repo.mkdir()
            wbs = repo / "WBS.md"
            wbs.write_text(MIN_WBS, encoding="utf-8")
            charge = repo / "forge" / "charge.md"
            charge.parent.mkdir(parents=True)
            charge.write_text(
                "## Active Sparks\n\n| Spark ID | Status |\n|----------|--------|\n| M1E1S1T1 | in progress |\n",
                encoding="utf-8",
            )
            payload = build_epic_spec_board_payload(root, repo_hint="r", wbs_rel="r/WBS.md")
            self.assertEqual(payload.get("profile"), "spark")
            self.assertEqual(payload.get("cards"), [])


class LivePilotTests(unittest.TestCase):
    def test_live_m1e3_apply_when_present(self) -> None:
        root = Path(__file__).resolve().parents[1]
        charge = root / "forge" / "charge.md"
        if not charge.is_file():
            self.skipTest("live forge-lenses charge missing")
        payload = build_epic_spec_board_payload(
            root.parent,
            repo_hint="forge-lenses",
            wbs_rel="forge-lenses/docs/requirements/WBS.md",
        )
        if payload.get("profile") != "epic":
            self.skipTest("not epic profile in live repo")
        cards = payload.get("cards") or []
        m1e3 = next((c for c in cards if c.get("epic_id") == "M1E3"), None)
        if not m1e3:
            self.skipTest("M1E3 not on live board")
        self.assertEqual(m1e3.get("column"), "apply")


class ChargeMutateNegativeTests(unittest.TestCase):
    def test_refuse_task_id(self) -> None:
        with TemporaryDirectory() as tmp:
            p = Path(tmp) / "charge.md"
            p.write_text(SAMPLE_EPIC_CHARGE, encoding="utf-8")
            with self.assertRaises(ValueError):
                upsert_epic_on_charge(
                    p,
                    epic_id="M1E3S2T4",
                    change_slug="x",
                    status="planned",
                    actor="a",
                    wbs_rel="WBS.md",
                )


if __name__ == "__main__":
    unittest.main()
