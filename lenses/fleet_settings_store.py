"""Persist Forge Fleet orchestrator settings under ``<workspace>/.lenses-local/fleet-settings.json``."""

from __future__ import annotations

import json
import os
import uuid
from pathlib import Path
from typing import Any

SETTINGS_FILENAME = "fleet-settings.json"
CURRENT_VERSION = 2

_DEFAULT: dict[str, Any] = {
    "version": CURRENT_VERSION,
    "nodes": [],
}


def settings_path(workspace_root: Path) -> Path:
    return workspace_root.resolve() / ".lenses-local" / SETTINGS_FILENAME


def _mask_token(t: str) -> str:
    s = (t or "").strip()
    if not s:
        return ""
    if len(s) <= 8:
        return "********"
    return s[:4] + "…" + s[-4:]


def _is_masked_token_placeholder(raw: str) -> bool:
    s = (raw or "").strip()
    if not s:
        return False
    if s.startswith("****"):
        return True
    if "…" in s[:16]:
        return True
    return False


def _normalize_node(n: Any, *, fallback_token: str | None) -> dict[str, Any] | None:
    if not isinstance(n, dict):
        return None
    base = str(n.get("base_url") or "").strip().rstrip("/")
    if not base:
        return None
    nid = str(n.get("id") or "").strip() or uuid.uuid4().hex[:12]
    tok = str(n.get("bearer_token") or "").strip()
    if not tok and fallback_token is not None:
        tok = fallback_token
    pri = n.get("priority")
    try:
        priority = int(pri) if pri is not None else 100
    except (TypeError, ValueError):
        priority = 100
    enabled = n.get("enabled", True)
    if isinstance(enabled, str):
        enabled = enabled.strip().lower() in ("1", "true", "yes", "on")
    else:
        enabled = bool(enabled)

    def _opt_float(key: str) -> float | None:
        v = n.get(key)
        if v is None or v == "":
            return None
        try:
            return float(v)
        except (TypeError, ValueError):
            return None

    max_cpu = _opt_float("max_cpu_percent")
    max_mem = _opt_float("max_memory_percent")
    if max_cpu is not None:
        max_cpu = max(0.0, min(100.0, max_cpu))
    if max_mem is not None:
        max_mem = max(0.0, min(100.0, max_mem))

    return {
        "id": nid,
        "base_url": base,
        "bearer_token": tok,
        "enabled": enabled,
        "priority": priority,
        "max_cpu_percent": max_cpu,
        "max_memory_percent": max_mem,
    }


def _migrate_v1_to_nodes(data: dict[str, Any]) -> list[dict[str, Any]]:
    base = str(data.get("base_url") or "").strip().rstrip("/")
    tok = str(data.get("bearer_token") or "").strip()
    if not base:
        return []
    return [
        {
            "id": "migrated",
            "base_url": base,
            "bearer_token": tok,
            "enabled": True,
            "priority": 10,
            "max_cpu_percent": None,
            "max_memory_percent": None,
        }
    ]


def load_raw(workspace_root: Path) -> dict[str, Any]:
    p = settings_path(workspace_root)
    if not p.is_file():
        return json.loads(json.dumps(_DEFAULT))
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return json.loads(json.dumps(_DEFAULT))
    if not isinstance(data, dict):
        return json.loads(json.dumps(_DEFAULT))

    out: dict[str, Any] = json.loads(json.dumps(_DEFAULT))
    nodes_in = data.get("nodes")
    if isinstance(nodes_in, list):
        merged: list[dict[str, Any]] = []
        for item in nodes_in:
            row = _normalize_node(item, fallback_token=None)
            if row:
                merged.append(row)
        out["nodes"] = merged
    else:
        out["nodes"] = _migrate_v1_to_nodes(data)
    out["version"] = CURRENT_VERSION
    return out


def save_raw(workspace_root: Path, data: dict[str, Any]) -> None:
    p = settings_path(workspace_root)
    p.parent.mkdir(parents=True, exist_ok=True)
    try:
        os.chmod(p.parent, 0o700)
    except OSError:
        pass
    tmp = p.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")
    tmp.replace(p)
    try:
        os.chmod(p, 0o600)
    except OSError:
        pass


def sanitize_for_get(data: dict[str, Any]) -> dict[str, Any]:
    raw_nodes = data.get("nodes")
    nodes_out: list[dict[str, Any]] = []
    if isinstance(raw_nodes, list):
        for n in raw_nodes:
            if not isinstance(n, dict):
                continue
            tok = str(n.get("bearer_token") or "")
            copy = dict(n)
            copy["bearer_token"] = _mask_token(tok)
            copy["bearer_token_configured"] = bool(tok)
            nodes_out.append(copy)
    return {"version": int(data.get("version") or CURRENT_VERSION), "nodes": nodes_out}


def merge_save(workspace_root: Path, incoming: dict[str, Any]) -> dict[str, Any]:
    cur = load_raw(workspace_root)
    cur_nodes = cur.get("nodes") if isinstance(cur.get("nodes"), list) else []
    by_id: dict[str, dict[str, Any]] = {}
    for x in cur_nodes:
        if isinstance(x, dict) and str(x.get("id") or "").strip():
            by_id[str(x["id"])] = dict(x)

    if "nodes" in incoming and isinstance(incoming.get("nodes"), list):
        merged: list[dict[str, Any]] = []
        for item in incoming["nodes"]:
            if not isinstance(item, dict):
                continue
            nid = str(item.get("id") or "").strip() or uuid.uuid4().hex[:12]
            prev_tok = str(by_id.get(nid, {}).get("bearer_token") or "")
            if "bearer_token" not in item:
                tok = prev_tok
            else:
                raw_tok = str(item.get("bearer_token") or "")
                if raw_tok and not _is_masked_token_placeholder(raw_tok):
                    tok = raw_tok
                elif raw_tok == "":
                    tok = ""
                else:
                    tok = prev_tok
            row = _normalize_node({**item, "id": nid, "bearer_token": tok}, fallback_token=None)
            if row:
                merged.append(row)
        cur["nodes"] = merged
        cur["version"] = CURRENT_VERSION
        return cur

    # Legacy single-field updates
    if "base_url" in incoming or "bearer_token" in incoming:
        nodes = list(cur.get("nodes") or [])
        if not nodes:
            base = str(incoming.get("base_url") or "").strip().rstrip("/")
            raw_tok = str(incoming.get("bearer_token") or "")
            tok = ""
            if raw_tok and not _is_masked_token_placeholder(raw_tok):
                tok = raw_tok
            if base or tok:
                nodes = [
                    {
                        "id": "default",
                        "base_url": base,
                        "bearer_token": tok,
                        "enabled": True,
                        "priority": 10,
                        "max_cpu_percent": None,
                        "max_memory_percent": None,
                    }
                ]
        else:
            n0 = dict(nodes[0])
            if "base_url" in incoming:
                n0["base_url"] = str(incoming.get("base_url") or "").strip().rstrip("/")
            if "bearer_token" in incoming:
                raw_tok = str(incoming.get("bearer_token") or "")
                if raw_tok and not _is_masked_token_placeholder(raw_tok):
                    n0["bearer_token"] = raw_tok
                elif raw_tok == "":
                    n0["bearer_token"] = ""
            nodes[0] = _normalize_node(n0, fallback_token=None) or nodes[0]
        cur["nodes"] = [x for x in nodes if isinstance(x, dict)]
        cur["version"] = CURRENT_VERSION
    return cur


def fleet_env_override_active() -> bool:
    return bool(str(os.environ.get("LENSES_FLEET_URL") or "").strip())


def fleet_nodes_for_client(workspace_root: Path) -> list[dict[str, Any]]:
    """
    Effective node list: when ``LENSES_FLEET_URL`` is set, a single synthetic node
    overrides saved routing (highest priority 0).
    """
    env_url = str(os.environ.get("LENSES_FLEET_URL") or "").strip().rstrip("/")
    env_tok = str(os.environ.get("LENSES_FLEET_TOKEN") or "").strip()
    if env_url:
        return [
            {
                "id": "env",
                "base_url": env_url,
                "bearer_token": env_tok,
                "enabled": True,
                "priority": 0,
                "max_cpu_percent": None,
                "max_memory_percent": None,
            }
        ]
    return [dict(x) for x in (load_raw(workspace_root).get("nodes") or []) if isinstance(x, dict)]
