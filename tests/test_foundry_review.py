"""Tests for Foundry review payloads."""

import json
from pathlib import Path


def test_build_review_unified_diff(tmp_path: Path):
    live = tmp_path / "live"
    run_dir = tmp_path / "run"
    worktree = run_dir / "worktree"
    machine = run_dir / "machine"
    (live / "src").mkdir(parents=True)
    (worktree / "src").mkdir(parents=True)
    (run_dir / "target" / "src").mkdir(parents=True)
    (live / "src" / "engine.py").write_text("def multiply(a, b):\n    return a - b\n", encoding="utf-8")
    (run_dir / "target" / "src" / "engine.py").write_text("def multiply(a, b):\n    return a + b\n", encoding="utf-8")
    (worktree / "src" / "engine.py").write_text("def multiply(a, b):\n    return a * b\n", encoding="utf-8")
    (machine).mkdir(parents=True)
    (machine / "proof.md").write_text("# Proof\n", encoding="utf-8")
    (machine / "phases.json").write_text(
        '{"phases":[{"name":"draft-unit","status":"ok","reasons":["fixture=/tmp/fix.json"]}]}',
        encoding="utf-8",
    )

    from lenses.foundry.review import build_review_payload

    out = build_review_payload(
        run_dir=run_dir,
        live_target=live,
        proof={"files_changed": ["src/engine.py"]},
        promoted=False,
        goal="fix multiply",
    )
    assert out["ok"] is True
    assert len(out["files"]) == 1
    assert "return a * b" in out["files"][0]["unified_diff"]
    assert out["narrative"]["root_cause"]


def test_build_review_fixture_before_after(tmp_path: Path):
    run_dir = tmp_path / "run"
    fixture = tmp_path / "fix.json"
    worktree = run_dir / "worktree"
    (worktree / "src").mkdir(parents=True)
    same = "def multiply(a, b):\n    return a * b\n"
    (worktree / "src" / "engine.py").write_text(same, encoding="utf-8")
    (run_dir / "target" / "src").mkdir(parents=True)
    (run_dir / "target" / "src" / "engine.py").write_text(same, encoding="utf-8")
    fixture.write_text(
        json.dumps(
            {
                "before": {"src/engine.py": "def multiply(a, b):\n    return a + b\n"},
                "files": {"src/engine.py": same},
            }
        ),
        encoding="utf-8",
    )
    machine = run_dir / "machine"
    machine.mkdir(parents=True)
    (machine / "phases.json").write_text(
        json.dumps({"phases": [{"name": "draft-unit", "reasons": [f"fixture={fixture}"]}]}),
        encoding="utf-8",
    )

    from lenses.foundry.review import build_review_payload

    live = tmp_path / "live"
    (live / "src").mkdir(parents=True)
    (live / "src" / "engine.py").write_text(same, encoding="utf-8")

    out = build_review_payload(
        run_dir=run_dir,
        live_target=live,
        proof={"files_changed": ["src/engine.py"]},
        promoted=False,
        goal="fix failing multiply",
        phases_raw=[{"name": "draft-unit", "reasons": [f"fixture={fixture}"]}],
    )
    assert out["files"][0]["source"] == "fixture"
    assert "return a + b" in out["files"][0]["unified_diff"]
    assert "return a * b" in out["files"][0]["unified_diff"]
    assert "multiply" in out["narrative"]["root_cause"].lower()

