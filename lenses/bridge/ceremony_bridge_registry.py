"""Load Sprint B4 ceremony bridge registry JSON and neutral registry.v1 ceremony intents."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any


def _b4_registry_path() -> Path:
    return Path(__file__).resolve().parent / "data" / "ceremony_bridge_registry.json"


def _v1_registry_path() -> Path:
    return Path(__file__).resolve().parent / "data" / "registry.v1.json"


@lru_cache(maxsize=1)
def load_ceremony_bridge_registry() -> dict[str, Any]:
    raw = _b4_registry_path().read_text(encoding="utf-8")
    return json.loads(raw)


@lru_cache(maxsize=1)
def load_registry_v1_ceremony_intents() -> dict[str, Any]:
    raw = _v1_registry_path().read_text(encoding="utf-8")
    data = json.loads(raw)
    ci = data.get("ceremony_intents")
    return ci if isinstance(ci, dict) else {}


def merged_ceremony_intents_payload() -> dict[str, Any]:
    """Neutral C1–C6 labels from registry.v1 plus B4 registry metadata."""
    v1 = load_registry_v1_ceremony_intents()
    b4 = load_ceremony_bridge_registry()
    out: dict[str, Any] = {}
    for cid in b4.get("neutral_intent_ids") or []:
        if not isinstance(cid, str):
            continue
        row = v1.get(cid)
        if isinstance(row, dict):
            out[cid] = {"intent_id": cid, **row}
        else:
            out[cid] = {"intent_id": cid, "neutral_label": cid}
    return {"intents": out, "registry_version": b4.get("registry_version")}
