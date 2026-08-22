"""Load Sprint B6 PDLC outcome bridge registry (JSON, vendor-neutral → Forge/PDLC hints)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def _registry_path() -> Path:
    return Path(__file__).resolve().parent / "data" / "pdlc_outcome_bridge_registry.json"


def load_pdlc_outcome_bridge_registry() -> dict[str, Any]:
    raw = _registry_path().read_text(encoding="utf-8")
    return json.loads(raw)
