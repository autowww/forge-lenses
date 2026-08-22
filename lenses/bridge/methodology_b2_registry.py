"""Load ``methodology_b2_registry.json`` (Forge profiles, gating, ingest defaults)."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any


@lru_cache(maxsize=1)
def load_methodology_b2_registry() -> dict[str, Any]:
    p = Path(__file__).resolve().parent / "data" / "methodology_b2_registry.json"
    data = json.loads(p.read_text(encoding="utf-8"))
    return data if isinstance(data, dict) else {}
