"""Read-only doc-hydration review pack surface (list + detail builders)."""

from __future__ import annotations

import json
from pathlib import Path

from lenses.doc_hydration_review import build_review_pack_detail, build_review_pack_list


def _make_pack(root: Path, name: str) -> Path:
    pack = root / "forge-platform" / "docs" / "hydration-runs" / name
    pack.mkdir(parents=True)
    (pack / "hydration-brief.md").write_text("# Hydration brief\n\nTrust boundary.\n", encoding="utf-8")
    (pack / "claim-inventory.json").write_text(
        json.dumps(
            {
                "schema": "forge.claim_inventory.v1",
                "claims": [{"claim_id": "forge.claim.candidate.aaa", "claim_text": "x", "status": "candidate"}],
            }
        ),
        encoding="utf-8",
    )
    (pack / "reviewer-decision-manifest.json").write_text(
        json.dumps({"schema": "forge.reviewer_decision_manifest.v1", "decisions": [{"decision": "promote_as_is"}]}),
        encoding="utf-8",
    )
    return pack


def test_list_empty_workspace(tmp_path: Path) -> None:
    payload = build_review_pack_list(tmp_path)
    assert payload["ok"] is True
    assert payload["read_only"] is True
    assert payload["count"] == 0


def test_list_and_detail_platform_pack(tmp_path: Path) -> None:
    _make_pack(tmp_path, "standout-pack")
    payload = build_review_pack_list(tmp_path)
    assert payload["count"] == 1
    pack = payload["packs"][0]
    assert pack["pack_id"] == "forge-platform:standout-pack"
    assert pack["claim_count"] == 1
    assert pack["reviewer_decisions"] == 1
    assert pack["has_brief"] is True

    detail = build_review_pack_detail(tmp_path, "forge-platform:standout-pack")
    assert detail["ok"] is True
    assert detail["claim_inventory"]["claims"][0]["status"] == "candidate"
    assert "Trust boundary" in detail["hydration_brief_markdown"]
    assert detail["reviewer_decision_manifest"]["decisions"][0]["decision"] == "promote_as_is"


def test_workcell_run_dirs_are_discovered(tmp_path: Path) -> None:
    run = tmp_path / "workbench" / "doc-hydration-runs" / "seed-x" / "arun_20260703T000000Z_ab12cd34"
    run.mkdir(parents=True)
    (run / "workcell_result.json").write_text(
        json.dumps(
            {
                "schema": "forge.workcell_result.v1",
                "forge_run_id": "frun_2026_07_03_demo",
                "status": "needs_approval",
            }
        ),
        encoding="utf-8",
    )
    payload = build_review_pack_list(tmp_path)
    assert payload["count"] == 1
    pack = payload["packs"][0]
    assert pack["pack_id"] == "workbench:seed-x/arun_20260703T000000Z_ab12cd34"
    assert pack["workcell_status"] == "needs_approval"
    assert pack["forge_run_id"] == "frun_2026_07_03_demo"


def test_detail_not_found(tmp_path: Path) -> None:
    detail = build_review_pack_detail(tmp_path, "forge-platform:missing")
    assert detail["ok"] is False
    assert detail["error"] == "review_pack_not_found"
