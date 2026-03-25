"""Optional workspace-registry.json merged with defaults."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


DEFAULTS: dict[str, Any] = {
    "external_urls": {
        "handbook": "https://blueprints.forgesdlc.com/",
        "forge": "https://forgesdlc.com/",
    },
    "ignore_paths": [],
    "website_labels": {},
}


def load_registry(lenses_repo_root: Path) -> dict[str, Any]:
    path = lenses_repo_root / "workspace-registry.json"
    merged = json.loads(json.dumps(DEFAULTS))
    if not path.is_file():
        return merged
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return merged
    if isinstance(data.get("external_urls"), dict):
        merged["external_urls"].update(data["external_urls"])
    if isinstance(data.get("ignore_paths"), list):
        merged["ignore_paths"] = [str(x) for x in data["ignore_paths"]]
    if isinstance(data.get("website_labels"), dict):
        merged["website_labels"].update(
            {str(k): str(v) for k, v in data["website_labels"].items()}
        )
    return merged


def should_ignore_child(name: str, registry: dict[str, Any]) -> bool:
    return name in set(registry.get("ignore_paths") or [])
