"""Aggregated LLM diagnostics for AI Setup (health, usage, probes, routing events)."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from lenses.llm_resolve import merged_secret_keys, providers_with_store
from lenses.llm_settings_store import load_raw, merged_openai_compat_base_url
from lenses.llm_usage_store import get_usage_summary, usage_path


def build_llm_diagnostics(workspace_root: Path) -> dict[str, Any]:
    """Shape for ``GET /api/llm/diagnostics``."""
    raw = load_raw(workspace_root)
    pv = providers_with_store(workspace_root)
    keys = merged_secret_keys(raw)
    compat_base = bool(str(merged_openai_compat_base_url(raw) or "").strip())
    ollama_url = bool(str(os.environ.get("OLLAMA_BASE_URL") or "").strip())
    summary = get_usage_summary(workspace_root)
    totals = summary.get("totals") if isinstance(summary.get("totals"), dict) else {}
    last_ok = summary.get("last_ok") if isinstance(summary.get("last_ok"), dict) else {}
    events = summary.get("recent_events") if isinstance(summary.get("recent_events"), list) else []
    probe_log = summary.get("probe_log") if isinstance(summary.get("probe_log"), list) else []

    connected = [pid for pid, ok in pv.items() if ok]
    connected_n = len(connected)
    mode = str(raw.get("routing_mode") or "single").strip().lower()

    last_probe_by_provider: dict[str, dict[str, Any]] = {}
    for row in reversed(probe_log):
        if not isinstance(row, dict):
            continue
        pid = str(row.get("provider") or "").strip().lower()
        if pid and pid not in last_probe_by_provider:
            last_probe_by_provider[pid] = {
                "ts": row.get("ts"),
                "action": row.get("action"),
                "ok": row.get("ok"),
                "detail": (str(row.get("detail") or "")[:240] or None),
            }

    providers_out: list[dict[str, Any]] = []
    for pid in ("anthropic", "openai", "gemini", "ollama", "openai_compatible"):
        t = totals.get(pid) if isinstance(totals.get(pid), dict) else {}
        prov_events = [e for e in events if isinstance(e, dict) and str(e.get("provider") or "").strip().lower() == pid]
        fails = [e for e in reversed(prov_events) if e.get("ok") is False][:8]
        if pid == "ollama":
            has_cred = ollama_url
        elif pid == "openai_compatible":
            has_cred = bool(keys.get(pid)) or compat_base
        else:
            has_cred = bool(keys.get(pid))
        providers_out.append(
            {
                "id": pid,
                "connected": bool(pv.get(pid)),
                "has_credential": has_cred,
                "last_ok_ts": last_ok.get(pid),
                "last_probe": last_probe_by_provider.get(pid),
                "totals": {
                    "prompt_tokens": int(t.get("prompt_tokens") or 0),
                    "completion_tokens": int(t.get("completion_tokens") or 0),
                    "total_tokens": int(t.get("total_tokens") or 0),
                    "requests": int(t.get("requests") or 0),
                    "attempts": int(t.get("attempts") or 0),
                    "failures": int(t.get("failures") or 0),
                },
                "recent_failures": [
                    {
                        "ts": e.get("ts"),
                        "error": e.get("error"),
                        "detail": e.get("detail"),
                        "model": e.get("model"),
                    }
                    for e in fails
                ],
            }
        )

    routing_events: list[dict[str, Any]] = []
    for e in reversed(events):
        if not isinstance(e, dict):
            continue
        if e.get("fallback_from") or e.get("studio_task_id") or (e.get("routing_source") and e.get("ok") is True):
            routing_events.append(
                {
                    "ts": e.get("ts"),
                    "provider": e.get("provider"),
                    "ok": e.get("ok"),
                    "model": e.get("model"),
                    "routing_source": e.get("routing_source"),
                    "routing_model": e.get("routing_model"),
                    "fallback_from": e.get("fallback_from"),
                    "studio_task_id": e.get("studio_task_id"),
                    "error": e.get("error"),
                }
            )
        if len(routing_events) >= 25:
            break
    routing_events.reverse()

    dismissed = bool(raw.get("first_run_wizard_dismissed"))
    first_run = connected_n == 0 and not dismissed

    next_step = "Connect at least one model source (cloud key, Ollama, or custom gateway), then use Try Chat."
    if connected_n == 0:
        next_step = "Start with one cloud API key or local Ollama — the cards above show what this host can reach."
    elif connected_n == 1:
        next_step = "Optional: add a second source to unlock smart routing and per-task overrides."
    else:
        next_step = "Run Discover / Health on each card, then open Try Chat to confirm routing."

    return {
        "ok": True,
        "routing_mode": mode,
        "connected_providers": connected_n,
        "connected_provider_ids": connected,
        "providers": providers_out,
        "routing_events": routing_events,
        "usage_path_hint": str(usage_path(workspace_root).relative_to(workspace_root.resolve())),
        "settings_path_hint": ".lenses-local/llm-settings.json",
        "first_run_recommended": first_run,
        "first_run_wizard_dismissed": dismissed,
        "next_recommended_step": next_step,
        "cost_note": "Dollar cost is not tracked locally; token counts come from provider responses when available.",
    }
