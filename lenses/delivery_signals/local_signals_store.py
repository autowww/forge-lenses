"""Load optional per-workspace delivery signal fixtures from ``.lenses-local/delivery-signals.json``."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


LOCAL_FILENAME = "delivery-signals.json"


def read_local_delivery_signals(workspace_root: Path) -> dict[str, Any] | None:
    """Parse ``.lenses-local/delivery-signals.json`` if present and well-formed.

    Expected top-level keys: ``schema_version`` (int), ``repos`` (map project name → fixture object).
    Returns ``None`` if missing, unreadable, or invalid.
    """
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
    """Optional checked-in demo for docs/tests (``lenses/fixtures/delivery-signals.demo.json``)."""
    p = lenses_package_root / "fixtures" / "delivery-signals.demo.json"
    if not p.is_file():
        return None
    try:
        raw = json.loads(p.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        return None
    return raw if isinstance(raw, dict) else None
