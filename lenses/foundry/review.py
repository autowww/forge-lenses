"""Build in-UI review payloads: proof summary, per-file diffs, post-promote git diff."""

from __future__ import annotations

import difflib
import json
import subprocess
from pathlib import Path
from typing import Any

from lenses.foundry.narrative import build_change_narrative


def _read_text(path: Path) -> str:
    if not path.is_file():
        return ""
    try:
        return path.read_text(encoding="utf-8")
    except OSError:
        return ""


def _read_json(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return data if isinstance(data, dict) else None


def _unified_diff_text(*, before: str, after: str, rel: str, before_label: str, after_label: str) -> str:
    before_lines = before.splitlines(keepends=True)
    after_lines = after.splitlines(keepends=True)
    if before_lines == after_lines:
        return ""
    return "".join(
        difflib.unified_diff(
            before_lines,
            after_lines,
            fromfile=f"{before_label}/{rel}",
            tofile=f"{after_label}/{rel}",
            lineterm="",
        )
    )


def _unified_diff_paths(*, live: Path, draft: Path, rel: str, before_label: str, after_label: str) -> str:
    return _unified_diff_text(
        before=_read_text(live),
        after=_read_text(draft),
        rel=rel,
        before_label=before_label,
        after_label=after_label,
    )


def _git_diff(cwd: Path, rel: str) -> str:
    proc = subprocess.run(
        ["git", "diff", "HEAD", "--", rel],
        cwd=str(cwd),
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        return ""
    return proc.stdout or ""


def _collect_changed_files(worktree: Path, baseline: Path) -> list[str]:
    changed: list[str] = []
    if not worktree.is_dir():
        return changed
    for path in worktree.rglob("*"):
        if not path.is_file():
            continue
        rel = path.relative_to(worktree).as_posix()
        if rel.startswith(".git/") or rel.startswith(".venv/"):
            continue
        dest = baseline / rel
        if not dest.is_file() or path.read_bytes() != dest.read_bytes():
            changed.append(rel)
    changed.sort()
    return changed


def _resolve_fixture(run_dir: Path, phases_raw: list[Any] | None) -> dict[str, Any] | None:
    from lenses.foundry.narrative import _fixture_path_from_model_report, _fixture_path_from_phases

    machine = run_dir / "machine"
    model_report = _read_json(machine / "model_report.json")
    path = _fixture_path_from_phases(phases_raw) or _fixture_path_from_model_report(model_report or {})
    if not path:
        return None
    return _read_json(Path(path))


def _diff_for_file(
    *,
    rel: str,
    run_dir: Path,
    live_target: Path,
    promoted: bool,
    fixture: dict[str, Any] | None,
) -> tuple[str, str]:
    worktree = run_dir / "worktree"
    baseline = run_dir / "target"

    if promoted:
        git = _git_diff(live_target, rel)
        if git.strip():
            return git, "git-live"

    git_wt = _git_diff(worktree, rel) if worktree.is_dir() else ""
    if git_wt.strip():
        return git_wt, "git-worktree"

    snap = _unified_diff_paths(
        live=baseline / rel,
        draft=worktree / rel,
        rel=rel,
        before_label="baseline",
        after_label="proposed",
    )
    if snap.strip():
        return snap, "baseline"

    live_vs = _unified_diff_paths(
        live=live_target / rel, draft=worktree / rel, rel=rel, before_label="live", after_label="proposed"
    )
    if live_vs.strip():
        return live_vs, "live"

    if isinstance(fixture, dict):
        before = (fixture.get("before") or {}).get(rel) if isinstance(fixture.get("before"), dict) else None
        after = (fixture.get("files") or {}).get(rel) if isinstance(fixture.get("files"), dict) else None
        if isinstance(before, str) and isinstance(after, str):
            fix = _unified_diff_text(
                before=before,
                after=after,
                rel=rel,
                before_label="before-fixture",
                after_label="after-fixture",
            )
            if fix.strip():
                return fix, "fixture"

    return "", "none"


def build_review_payload(
    *,
    run_dir: Path,
    live_target: Path,
    proof: dict[str, Any] | None,
    promoted: bool,
    goal: str = "",
    phases_raw: list[Any] | None = None,
    plan: dict[str, Any] | None = None,
) -> dict[str, Any]:
    machine = run_dir / "machine"
    worktree = run_dir / "worktree"
    proof_markdown = _read_text(machine / "proof.md")
    fixture = _resolve_fixture(run_dir, phases_raw)

    raw_files = proof.get("files_changed") if isinstance(proof, dict) else None
    files_changed: list[str] = []
    if isinstance(raw_files, list):
        files_changed = sorted({str(x) for x in raw_files if str(x).strip()})
    if not files_changed:
        files_changed = _collect_changed_files(worktree, run_dir / "target")

    file_rows: list[dict[str, Any]] = []
    for rel in files_changed:
        unified, source = _diff_for_file(
            rel=rel,
            run_dir=run_dir,
            live_target=live_target,
            promoted=promoted,
            fixture=fixture,
        )
        file_rows.append(
            {
                "path": rel,
                "unified_diff": unified,
                "has_changes": bool(unified.strip()),
                "source": source,
            }
        )

    narrative = build_change_narrative(
        run_dir=run_dir,
        goal=goal,
        proof=proof,
        phases_raw=phases_raw,
        plan=plan,
    )
    if file_rows and narrative.get("ok"):
        from lenses.foundry.narrative import _change_summary_from_diff

        narrative["change_summary"] = _change_summary_from_diff(
            file_rows[0]["path"],
            str(file_rows[0].get("unified_diff") or ""),
            goal,
        )

    return {
        "ok": True,
        "proof_markdown": proof_markdown,
        "files": file_rows,
        "promoted": promoted,
        "narrative": narrative,
    }
