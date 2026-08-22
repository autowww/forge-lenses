"""Load Sprint B3 agentic bridge registry JSON."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any


def _registry_path() -> Path:
    return Path(__file__).resolve().parent / "data" / "agentic_bridge_registry.json"


@lru_cache(maxsize=1)
def load_agentic_bridge_registry() -> dict[str, Any]:
    raw = _registry_path().read_text(encoding="utf-8")
    return json.loads(raw)
