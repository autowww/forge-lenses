"""Persist discovered model catalogs for URL-backed LLM sources under ``.lenses-local/``.

Used to detect **new** model ids after a previous snapshot (Ollama + OpenAI-compatible gateway).
"""

from __future__ import annotations

import hashlib
import json
import os
import urllib.parse
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from lenses import llm_settings_store
from lenses.llm_completions import ollama_daemon_status
from lenses.llm_provider_probe import discover_models
from lenses.llm_settings_store import merged_openai_compat_base_url

SNAPSHOT_FILENAME = "llm-model-catalog-snapshot.json"
_CURRENT_VERSION = 1

_DEFAULT: dict[str, Any] = {"version": _CURRENT_VERSION, "sources": {}}


def snapshot_path(workspace_root: Path) -> Path:
    return workspace_root.resolve() / ".lenses-local" / SNAPSHOT_FILENAME


def normalize_origin(url: str) -> str:
    """Stable origin string for snapshot keys (scheme + host, default ports omitted)."""
    u = (url or "").strip().rstrip("/")
    if not u:
        return ""
    parts = urllib.parse.urlsplit(u if "://" in u else f"http://{u}")
    scheme = (parts.scheme or "http").lower()
    netloc = (parts.netloc or "").lower()
    if not netloc:
        return ""
    host = netloc
    if scheme == "https" and host.endswith(":443"):
        host = host[:-4]
    elif scheme == "http" and host.endswith(":80"):
        host = host[:-3]
    return f"{scheme}://{host}"


def source_key(provider_id: str, origin: str) -> str:
    no = normalize_origin(origin)
    return f"{provider_id.strip().lower()}|{no}"


def _load(workspace_root: Path) -> dict[str, Any]:
    p = snapshot_path(workspace_root)
    if not p.is_file():
        return json.loads(json.dumps(_DEFAULT))
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return json.loads(json.dumps(_DEFAULT))
    if not isinstance(data, dict):
        return json.loads(json.dumps(_DEFAULT))
    out = json.loads(json.dumps(_DEFAULT))
    for k, v in data.items():
        if k in out:
            out[k] = v
    if not isinstance(out.get("sources"), dict):
        out["sources"] = {}
    return out


def _save(workspace_root: Path, data: dict[str, Any]) -> None:
    p = snapshot_path(workspace_root)
    p.parent.mkdir(parents=True, exist_ok=True)
    try:
        os.chmod(p.parent, 0o700)
    except OSError:
        pass
    tmp = p.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")
    tmp.replace(p)


def diff_new_models(previous: list[str], current: list[str]) -> list[str]:
    prev = {str(x).strip() for x in previous if str(x).strip()}
    cur = [str(x).strip() for x in current if str(x).strip()]
    return sorted({m for m in cur if m not in prev})


def _url_sources_to_probe(workspace_root: Path) -> list[tuple[str, str]]:
    """``(provider_id, origin)`` pairs for Ollama (when reachable) and OpenAI-compatible base URL."""
    out: list[tuple[str, str]] = []
    raw = llm_settings_store.load_raw(workspace_root)

    st = ollama_daemon_status()
    base = str(st.get("base") or "").strip().rstrip("/")
    if st.get("configured") and base and st.get("reachable"):
        out.append(("ollama", base))

    b = merged_openai_compat_base_url(raw).strip().rstrip("/")
    if b:
        out.append(("openai_compatible", b))

    return out


def _provider_label(provider_id: str) -> str:
    return {
        "ollama": "Ollama",
        "openai_compatible": "Custom gateway",
    }.get(provider_id, provider_id)


def refresh_catalog_notifications(workspace_root: Path) -> dict[str, Any]:
    """
    Probe URL-backed catalogs, diff against ``.lenses-local/llm-model-catalog-snapshot.json``,
    persist the updated snapshot, and return structured notifications for **new** model ids only.

    First successful snapshot for a source key establishes a baseline (no notifications).
    """
    urls = _url_sources_to_probe(workspace_root)
    if not urls:
        return {"ok": True, "notifications": [], "checked": []}

    notifications: list[dict[str, Any]] = []
    checked: list[dict[str, Any]] = []
    snap = _load(workspace_root)
    sources: dict[str, Any] = dict(snap.get("sources") or {})

    for provider_id, origin in urls:
        key = source_key(provider_id, origin)
        if key.endswith("|") or not normalize_origin(origin):
            checked.append({"source_key": key, "skipped": True, "reason": "bad_origin"})
            continue

        prev_entry = sources.get(key) if isinstance(sources.get(key), dict) else {}
        prev_ids_raw = prev_entry.get("model_ids") if isinstance(prev_entry, dict) else None
        if not isinstance(prev_ids_raw, list):
            prev_ids_raw = []
        prev_ids = [str(x).strip() for x in prev_ids_raw if isinstance(x, (str, int)) and str(x).strip()]

        out = discover_models(workspace_root, provider_id)
        if not out.get("ok"):
            checked.append(
                {
                    "source_key": key,
                    "ok": False,
                    "error": out.get("error"),
                    "detail": out.get("detail"),
                }
            )
            continue

        raw_models = out.get("models")
        current = (
            [str(x).strip() for x in raw_models if str(x).strip()]
            if isinstance(raw_models, list)
            else []
        )
        current.sort()

        if not prev_ids:
            sources[key] = {
                "provider_id": provider_id,
                "origin": normalize_origin(origin),
                "model_ids": current,
                "checked_at": datetime.now(timezone.utc).isoformat(),
            }
            checked.append(
                {
                    "source_key": key,
                    "baseline": True,
                    "model_count": len(current),
                }
            )
            continue

        new_models = diff_new_models(prev_ids, current)
        sources[key] = {
            "provider_id": provider_id,
            "origin": normalize_origin(origin),
            "model_ids": current,
            "checked_at": datetime.now(timezone.utc).isoformat(),
        }

        if new_models:
            digest = hashlib.sha256(",".join(new_models).encode("utf-8")).hexdigest()[:16]
            nid = f"llm-catalog|{key}|{digest}"
            origin_disp = normalize_origin(origin) or origin
            shown = new_models[:12]
            extra = len(new_models) - len(shown)
            tail = f" (+{extra} more)" if extra > 0 else ""
            model_summary = ", ".join(shown) + tail
            first = new_models[0]
            to_q = f"/chat?provider={urllib.parse.quote(provider_id)}&model={urllib.parse.quote(first)}&studio_task_id=chat_assistant"
            notifications.append(
                {
                    "id": nid,
                    "provider_id": provider_id,
                    "origin": origin_disp,
                    "new_models": new_models,
                    "headline": f"New model{'s' if len(new_models) > 1 else ''} at {_provider_label(provider_id)}",
                    "scope_label": origin_disp,
                    "action_hint": f"Try in Chat: {model_summary}",
                    "try_chat_to": to_q,
                }
            )

        checked.append(
            {
                "source_key": key,
                "ok": True,
                "new_count": len(new_models),
                "model_count": len(current),
            }
        )

    snap["version"] = _CURRENT_VERSION
    snap["sources"] = sources
    _save(workspace_root, snap)

    return {"ok": True, "notifications": notifications, "checked": checked}
