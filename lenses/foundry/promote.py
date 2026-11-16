"""Promote changed files from a DF worktree to the live target repo."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path
from typing import Any


def _git(cwd: Path, *args: str) -> tuple[int, str, str]:
    proc = subprocess.run(
        ["git", *args],
        cwd=str(cwd),
        capture_output=True,
        text=True,
    )
    return proc.returncode, proc.stdout or "", proc.stderr or ""


def promote_from_run_dir(
    *,
    run_dir: Path,
    live_target: Path,
    promote_scope: str = "file",
) -> dict[str, Any]:
    worktree = run_dir / "worktree"
    if not worktree.is_dir():
        return {"ok": False, "error": "worktree_missing"}

    changed: list[str] = []
    for path in worktree.rglob("*"):
        if not path.is_file():
            continue
        rel = path.relative_to(worktree).as_posix()
        if rel.startswith(".git/"):
            continue
        dest = live_target / rel
        if not dest.is_file():
            changed.append(rel)
            continue
        if path.read_bytes() != dest.read_bytes():
            changed.append(rel)

    if not changed:
        return {"ok": True, "messages": ["no file changes to promote"], "changed_files": []}

    if promote_scope == "repo":
        code, _, err = _git(live_target, "status", "--porcelain")
        if code != 0:
            return {"ok": False, "error": "git_status_failed", "detail": err}
        if _.strip():
            return {"ok": False, "error": "live_repo_dirty", "detail": "repo must be clean for promote_scope=repo"}

    for rel in changed:
        src = worktree / rel
        dest = live_target / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        if promote_scope == "file":
            code, out, err = _git(live_target, "status", "--porcelain", "--", rel)
            if code == 0 and out.strip():
                return {"ok": False, "error": "path_dirty", "path": rel, "detail": out.strip()}
        shutil.copy2(src, dest)

    return {"ok": True, "messages": [f"promoted {len(changed)} file(s)"], "changed_files": changed}
