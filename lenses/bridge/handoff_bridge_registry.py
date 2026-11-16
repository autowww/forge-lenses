"""Load Sprint B5 handoff bridge registry JSON."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any


def _path() -> Path:
    return Path(__file__).resolve().parent / "data" / "handoff_bridge_registry.json"


@lru_cache(maxsize=1)
def load_handoff_bridge_registry() -> dict[str, Any]:
    return json.loads(_path().read_text(encoding="utf-8"))
