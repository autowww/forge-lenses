"""Unified diff text for patch preview (read-only against source checkout)."""

from __future__ import annotations

import difflib
from pathlib import Path


def unified_diff_preview(repo_root: Path, *, rel_path: str, new_content: str) -> str:
    """Build a unified diff without writing ``new_content`` to the repo."""
    rel = str(rel_path or "").strip()
    old = ""
    p = (repo_root / rel).resolve()
    try:
        p.relative_to(repo_root.resolve())
    except ValueError:
        return ""
    if p.is_file():
        try:
            old = p.read_text(encoding="utf-8")
        except OSError:
            old = ""
    a = old.splitlines(keepends=True)
    b = new_content.splitlines(keepends=True)
    return "".join(difflib.unified_diff(a, b, fromfile=f"a/{rel}", tofile=f"b/{rel}"))
