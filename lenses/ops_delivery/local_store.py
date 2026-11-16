"""Local fixture: ``.lenses-local/ops-delivery.json``."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

LOCAL_FILENAME = "ops-delivery.json"


def read_local_ops_delivery(workspace_root: Path) -> dict[str, Any] | None:
    path = workspace_root / ".lenses-local" / LOCAL_FILENAME
    if not path.is_file():
        return None
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        return None
    return raw if isinstance(raw, dict) else None


def load_demo_fixture(lenses_package_root: Path) -> dict[str, Any] | None:
    p = lenses_package_root / "fixtures" / "ops-delivery.demo.json"
    if not p.is_file():
        return None
    try:
        raw = json.loads(p.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return raw if isinstance(raw, dict) else None
