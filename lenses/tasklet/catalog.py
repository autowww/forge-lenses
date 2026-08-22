"""Scan persisted TaskletRun JSON files (workspace-local, no network)."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any


def _runs_dir(workspace_root: Path) -> Path:
    return workspace_root.resolve() / ".lenses-local" / "tasklet-runs"


def list_tasklet_runs(workspace_root: Path, *, limit: int = 500) -> list[dict[str, Any]]:
    """Recent tasklet runs (newest mtime first)."""
    d = _runs_dir(workspace_root)
    if not d.is_dir():
        return []
    paths = sorted(d.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
    out: list[dict[str, Any]] = []
    for p in paths:
        try:
            raw = json.loads(p.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if isinstance(raw, dict):
            out.append(raw)
        if len(out) >= max(1, limit):
            break
    return out


def list_tasklet_runs_for_project(
    workspace_root: Path,
    project_slug: str,
    *,
    limit: int = 24,
) -> list[dict[str, Any]]:
    """All runs for a project (best-effort; sorted by updated_at desc when present)."""
    want = str(project_slug or "").strip()
    if not want:
        return []
    rows: list[tuple[str, dict[str, Any]]] = []
    d = _runs_dir(workspace_root)
    if not d.is_dir():
        return []
    for p in d.glob("*.json"):
        try:
            raw = json.loads(p.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if not isinstance(raw, dict):
            continue
        if str(raw.get("project_slug") or "").strip() != want:
            continue
        ts = str(raw.get("updated_at") or raw.get("created_at") or "")
        rows.append((ts, raw))
    rows.sort(key=lambda x: x[0], reverse=True)
    return [r for _, r in rows[: max(1, limit)]]


def safe_filename_run_id(run_id: str) -> str:
    safe = str(run_id or "").strip().replace(os.sep, "_").replace("/", "_")
    if not safe or ".." in safe:
        raise ValueError("invalid_tasklet_run_id")
    return safe
