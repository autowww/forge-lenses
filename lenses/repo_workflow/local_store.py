"""Local-first store: ``.lenses-local/repo-workflow.json``."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

LOCAL_FILENAME = "repo-workflow.json"


def read_local_repo_workflow(workspace_root: Path) -> dict[str, Any] | None:
    path = workspace_root / ".lenses-local" / LOCAL_FILENAME
    if not path.is_file():
        return None
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        return None
    if not isinstance(raw, dict):
        return None
    repos = raw.get("repos")
    if repos is not None and not isinstance(repos, dict):
        return None
    return raw


def load_demo_fixture(lenses_package_root: Path) -> dict[str, Any] | None:
    p = lenses_package_root / "fixtures" / "repo-workflow.demo.json"
    if not p.is_file():
        return None
    try:
        raw = json.loads(p.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return raw if isinstance(raw, dict) else None
