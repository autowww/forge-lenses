"""Tests for post-apply verification helpers."""

from __future__ import annotations

import tempfile
from pathlib import Path

from lenses.docs_health.verification_pipeline import (
    check_markdown_links_for_paths,
    run_contract_verification,
    run_post_apply_verification,
)


def test_broken_relative_link_detected() -> None:
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        (root / "a.md").write_text("[x](missing.md)\n", encoding="utf-8")
        r = check_markdown_links_for_paths(root, ["a.md"])
        assert r["ok"] is False
        assert r["broken_count"] >= 1


def test_contract_verification_skipped_when_empty() -> None:
    with tempfile.TemporaryDirectory() as td:
        r = run_contract_verification(Path(td), {})
        assert r.get("skipped") is True


def test_contract_verification_runs_true_cmd() -> None:
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        contract = {
            "post_apply_verification": {
                "commands": [{"name": "noop", "cmd": ["true"], "cwd": ".", "timeout_sec": 5}],
            }
        }
        r = run_contract_verification(root, contract)
        assert r.get("skipped") is False
        assert r.get("ok") is True


def test_post_apply_bundle_ok_for_valid_link(tmp_path: Path) -> None:
    (tmp_path / "b.md").write_text("y\n", encoding="utf-8")
    (tmp_path / "a.md").write_text("[b](b.md)\n", encoding="utf-8")
    r = run_post_apply_verification(tmp_path, applied_rel_paths=["a.md"], contract={})
    assert r["ok"] is True
