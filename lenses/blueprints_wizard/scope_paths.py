"""Validate WBS / Roadmap relative paths against workspace (same rules as lenses.serve)."""

from __future__ import annotations

from pathlib import Path


def safe_wbs_file(workspace_root: Path, rel: str) -> Path | None:
    if not rel or ".." in rel.split("/") or rel.startswith(("/", "\\")):
        return None
    rel_norm = rel.replace("\\", "/").strip("/")
    candidate = (workspace_root / rel_norm).resolve()
    wr = workspace_root.resolve()
    try:
        candidate.relative_to(wr)
    except ValueError:
        return None
    parts = candidate.parts
    if "requirements" not in parts:
        return None
    if candidate.name != "WBS.md":
        return None
    if not candidate.is_file():
        return None
    return candidate


def safe_roadmap_file(workspace_root: Path, rel: str) -> Path | None:
    if not rel or ".." in rel.split("/") or rel.startswith(("/", "\\")):
        return None
    rel_norm = rel.replace("\\", "/").strip("/")
    candidate = (workspace_root / rel_norm).resolve()
    wr = workspace_root.resolve()
    try:
        candidate.relative_to(wr)
    except ValueError:
        return None
    parts = candidate.parts
    if "docs" not in parts:
        return None
    if candidate.name != "ROADMAP.md":
        return None
    if not candidate.is_file():
        return None
    return candidate
