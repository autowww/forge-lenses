"""Resolve effective model id from env + file settings + routing rules."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from lenses import llm_settings_store
from lenses.llm_classifier import classify_gemini, classify_openai
from lenses.llm_routing import (
    RequestClassification,
    adaptive_adjust,
    parse_tier,
    pick_from_ordered,
    quality_order_for_provider,
    refinement_shift_toward_cheaper,
    ordered_model_list,
)
from lenses.llm_settings_store import merge_key, merged_openai_compat_base_url
from lenses.llm_smart_routes import apply_privacy_policy, smart_provider_for_task

# Defaults when env not set (same as llm_chat)
_DEFAULT_MAIN = {
    "anthropic": "claude-3-5-haiku-20241022",
    "openai": "gpt-4o-mini",
    "gemini": "gemini-2.0-flash",
    "ollama": "llama3.2",
    "openai_compatible": "gpt-4o-mini",
}


def _env_trim(key: str) -> str:
    return (os.environ.get(key) or "").strip()


def _file_secret(val: Any) -> str:
    """Return trimmed file key string; ignore non-strings (corrupt or masked shapes)."""
    if val is None:
        return ""
    if isinstance(val, str):
        return val.strip()
    return ""


def merged_secret_keys(settings: dict[str, Any]) -> dict[str, str]:
    fk = settings.get("keys") if isinstance(settings.get("keys"), dict) else {}
    keys: dict[str, str] = {}
    keys["anthropic"] = merge_key(_env_trim("ANTHROPIC_API_KEY"), _file_secret(fk.get("anthropic")))
    keys["openai"] = merge_key(_env_trim("OPENAI_API_KEY"), _file_secret(fk.get("openai")))
    keys["gemini"] = merge_key(
        _env_trim("GOOGLE_API_KEY") or _env_trim("GEMINI_API_KEY"),
        _file_secret(fk.get("gemini")),
    )
    keys["openai_compatible"] = merge_key(_env_trim("LENSES_OPENAI_COMPAT_KEY"), _file_secret(fk.get("openai_compatible")))
    return keys


def _default_catalog(provider: str) -> set[str]:
    return set(quality_order_for_provider(provider))


def _classifier_model_ids(raw: dict[str, Any]) -> tuple[str, str]:
    cm = raw.get("classifier_models") if isinstance(raw.get("classifier_models"), dict) else {}
    o = str(cm.get("openai", "") or "").strip()
    g = str(cm.get("gemini", "") or "").strip()
    return o, g


def resolve_effective_model(
    provider: str,
    *,
    workspace_root: Path | None,
    model_override: str | None,
    refine: bool,
    user_message: str,
    settings_raw: dict[str, Any] | None = None,
) -> tuple[str | None, str | None, dict[str, Any]]:
    """
    Returns (model_id, error_code, debug_info).

    If model_override is set, returns it immediately (no routing).
    """
    pid = provider.lower().strip()
    dbg: dict[str, Any] = {"provider": pid, "refine": refine}

    if model_override and str(model_override).strip():
        m = str(model_override).strip()
        dbg["source"] = "override"
        return m, None, dbg

    if workspace_root is None:
        dbg["source"] = "env_defaults"
        return None, None, dbg

    raw = settings_raw if settings_raw is not None else llm_settings_store.load_raw(workspace_root)
    keys = merged_secret_keys(raw)
    cl_openai, cl_gemini = _classifier_model_ids(raw)

    mm = raw.get("main_models") if isinstance(raw.get("main_models"), dict) else {}
    main = str(mm.get(pid, "") or "").strip() or _DEFAULT_MAIN.get(pid, _DEFAULT_MAIN["openai"])

    advanced = bool(raw.get("advanced_ui"))
    auto = bool(raw.get("auto_model"))
    adaptive = bool(raw.get("adaptive_autoselection"))
    tier = parse_tier(str(raw.get("tier", "MED")))
    refine_steps = int(raw.get("refine_cheaper_steps", 2) or 2)
    refine_steps = max(0, min(20, refine_steps))

    pools_raw = raw.get("pools") if isinstance(raw.get("pools"), dict) else {}
    pool_list_raw = pools_raw.get(pid) if isinstance(pools_raw, dict) else None
    pool_list_order: list[str] | None = None
    if isinstance(pool_list_raw, list) and pool_list_raw:
        pool_list_order = [str(x).strip() for x in pool_list_raw if str(x).strip()]
        pool = set(pool_list_order)
    else:
        pool = _default_catalog(pid)

    catalog = _default_catalog(pid)
    if pid in ("ollama", "openai_compatible") and not pool:
        pool = {main}
        catalog = {main}

    if pid in ("ollama", "openai_compatible"):
        if not advanced or not auto:
            dbg["source"] = "manual_main"
            return main, None, dbg
        ordered = ordered_model_list(pid, pool, catalog, pool_list_order)
        if not ordered:
            ordered = [main]
        mid = pick_from_ordered(ordered, tier, main)
        if refine:
            mid = refinement_shift_toward_cheaper(ordered, mid, refine_steps)
        dbg["source"] = "auto_simple"
        dbg["model"] = mid
        return mid, None, dbg

    if pid == "anthropic":
        if not advanced or not auto:
            dbg["source"] = "manual_main"
            return main, None, dbg
        ordered = ordered_model_list(pid, pool, catalog, pool_list_order)
        if not ordered:
            dbg["source"] = "manual_main_fallback"
            return main, None, dbg
        mid = pick_from_ordered(ordered, tier, main)
        cls: RequestClassification | None = None
        if adaptive and keys.get("anthropic"):
            cls = _classify_anthropic_via_openai(keys, user_message, cl_openai)
        if cls is not None:
            mid = adaptive_adjust(ordered, tier, main, cls)
        if refine:
            mid = refinement_shift_toward_cheaper(ordered, mid, refine_steps)
        dbg["source"] = "auto_anthropic"
        dbg["model"] = mid
        return mid, None, dbg

    if pid == "openai":
        if not advanced or not auto:
            dbg["source"] = "manual_main"
            return main, None, dbg
        ordered = ordered_model_list(pid, pool, catalog, pool_list_order)
        if not ordered:
            dbg["source"] = "manual_main_fallback"
            return main, None, dbg
        mid = pick_from_ordered(ordered, tier, main)
        cls: RequestClassification | None = None
        if adaptive and keys.get("openai"):
            cls = classify_openai(keys["openai"], user_message, model=cl_openai or None)
        if cls is not None:
            mid = adaptive_adjust(ordered, tier, main, cls)
        if refine:
            mid = refinement_shift_toward_cheaper(ordered, mid, refine_steps)
        dbg["source"] = "auto_openai"
        dbg["model"] = mid
        return mid, None, dbg

    if pid == "gemini":
        if not advanced or not auto:
            dbg["source"] = "manual_main"
            return main, None, dbg
        ordered = ordered_model_list(pid, pool, catalog, pool_list_order)
        if not ordered:
            dbg["source"] = "manual_main_fallback"
            return main, None, dbg
        mid = pick_from_ordered(ordered, tier, main)
        cls: RequestClassification | None = None
        if adaptive and keys.get("gemini"):
            cls = classify_gemini(keys["gemini"], user_message, model=cl_gemini or None)
        if cls is not None:
            mid = adaptive_adjust(ordered, tier, main, cls)
        if refine:
            mid = refinement_shift_toward_cheaper(ordered, mid, refine_steps)
        dbg["source"] = "auto_gemini"
        dbg["model"] = mid
        return mid, None, dbg

    dbg["source"] = "manual_main"
    return main, None, dbg


def _classify_anthropic_via_openai(
    keys: dict[str, str], user_message: str, classifier_openai_model: str = ""
) -> RequestClassification | None:
    """Anthropic has no classifier in llm_classifier; reuse OpenAI key if present for routing."""
    k = keys.get("openai") or ""
    if not k:
        return None
    return classify_openai(k, user_message, model=classifier_openai_model or None)


def providers_with_store(workspace_root: Path | None) -> dict[str, bool]:
    """Merge env presence with file keys for /api/llm/providers."""
    base = {
        "anthropic": bool(_env_trim("ANTHROPIC_API_KEY")),
        "openai": bool(_env_trim("OPENAI_API_KEY")),
        "gemini": bool(_env_trim("GOOGLE_API_KEY") or _env_trim("GEMINI_API_KEY")),
        "ollama": bool(_env_trim("OLLAMA_BASE_URL")),
        "openai_compatible": bool(_env_trim("LENSES_OPENAI_COMPAT_BASE_URL")),
    }
    if workspace_root is None:
        return base
    raw = llm_settings_store.load_raw(workspace_root)
    if merged_openai_compat_base_url(raw):
        base["openai_compatible"] = True
    mk = merged_secret_keys(raw)
    for p in base:
        if mk.get(p):
            base[p] = True
    return base


def _empty_route_entry() -> dict[str, Any]:
    return {
        "provider": "",
        "model": "",
        "model_stack": [],
        "fallback_provider": "",
        "fallback_model": "",
        "privacy": "cloud_allowed",
    }


def _normalized_model_stack(entry: dict[str, Any]) -> list[str]:
    """Ordered model ids for a task route; first entry is the only one used by routing today."""
    acc: list[str] = []
    ms = entry.get("model_stack")
    if isinstance(ms, list):
        for x in ms:
            s = str(x or "").strip()
            if s:
                acc.append(s)
    if not acc:
        m = str(entry.get("model") or "").strip()
        if m:
            acc.append(m)
    return acc


def _task_route_entry(raw: dict[str, Any], tid: str) -> dict[str, Any]:
    tr = raw.get("task_routes")
    if not isinstance(tr, dict):
        return _empty_route_entry()
    entry = tr.get(tid)
    if not isinstance(entry, dict):
        return _empty_route_entry()
    pr = str(entry.get("privacy") or "").strip().lower()
    if pr not in ("local_only", "prefer_local", "cloud_allowed"):
        pr = "cloud_allowed"
    stack = _normalized_model_stack(entry)
    eff_model = stack[0] if stack else ""
    return {
        "provider": str(entry.get("provider") or "").strip(),
        "model": eff_model,
        "model_stack": stack,
        "fallback_provider": str(entry.get("fallback_provider") or "").strip(),
        "fallback_model": str(entry.get("fallback_model") or "").strip(),
        "privacy": pr,
    }


def _privacy_for_task(raw: dict[str, Any], tid: str) -> str:
    return _task_route_entry(raw, tid)["privacy"]


_ROUTING_PREVIEW_OVERLAY_KEYS = frozenset(
    {
        "routing_mode",
        "tier",
        "provider",
        "advanced_ui",
        "auto_model",
        "adaptive_autoselection",
        "refine_cheaper_steps",
        "main_models",
        "pools",
        "classifier_models",
        "task_routes",
    }
)


def merge_routing_preview_overlay(base: dict[str, Any], overlay: dict[str, Any]) -> dict[str, Any]:
    """Shallow merge for in-memory routing preview (does not persist)."""
    raw: dict[str, Any] = json.loads(json.dumps(base))
    for k, v in overlay.items():
        if k not in _ROUTING_PREVIEW_OVERLAY_KEYS:
            continue
        if k == "task_routes" and isinstance(v, dict):
            tr = dict(raw.get("task_routes") or {})
            for tid, row in v.items():
                if not isinstance(row, dict):
                    continue
                tks = str(tid).strip()
                ex = dict(tr.get(tks) or _empty_route_entry())
                for fk in ("provider", "model", "fallback_provider", "fallback_model", "privacy"):
                    if fk in row:
                        ex[fk] = str(row[fk] or "").strip()
                if "model_stack" in row and isinstance(row.get("model_stack"), list):
                    stack = [str(x or "").strip() for x in row["model_stack"] if str(x or "").strip()]
                    ex["model_stack"] = stack
                    ex["model"] = stack[0] if stack else str(ex.get("model") or "").strip()
                pr = str(ex.get("privacy") or "cloud_allowed").strip().lower()
                ex["privacy"] = pr if pr in ("local_only", "prefer_local", "cloud_allowed") else "cloud_allowed"
                tr[tks] = ex
            raw["task_routes"] = tr
        elif isinstance(v, bool) and k in ("advanced_ui", "auto_model", "adaptive_autoselection"):
            raw[k] = v
        elif k == "refine_cheaper_steps":
            try:
                raw[k] = max(0, min(20, int(v)))
            except (TypeError, ValueError):
                pass
        elif k == "routing_mode" and isinstance(v, str):
            raw[k] = v.strip().lower()
        elif k == "tier" and isinstance(v, str):
            raw[k] = v.strip().upper()
        elif k == "provider" and isinstance(v, str):
            raw[k] = v.strip()
        elif isinstance(v, dict) and k in ("main_models", "pools", "classifier_models"):
            cur = dict(raw.get(k) or {})
            for kk, vv in v.items():
                cur[str(kk)] = vv
            raw[k] = cur
    return raw


def effective_provider_for_task(
    raw: dict[str, Any],
    studio_task_id: str | None,
    request_provider: str,
    model_override: str | None,
    *,
    workspace_root: Path | None = None,
) -> tuple[str, str | None, str | None]:
    """Resolve Studio task to (provider, model_override, privacy_warn_or_none)."""
    default_p = str(raw.get("provider") or "openai").strip() or "openai"
    req_p = (request_provider or "").strip() or default_p
    tid = (studio_task_id or "").strip()
    pv = providers_with_store(workspace_root) if workspace_root is not None else providers_with_store(None)
    if not tid:
        p, mo, _warn = apply_privacy_policy(req_p, model_override, "cloud_allowed", pv)
        return p, mo, None

    mode = str(raw.get("routing_mode") or "single").strip().lower()
    if mode not in ("single", "smart", "advanced"):
        mode = "single"
    privacy = _privacy_for_task(raw, tid)
    entry = _task_route_entry(raw, tid)

    if mode == "smart":
        sp, _note = smart_provider_for_task(tid, default_p, raw, pv)
        p2, mo2, w = apply_privacy_policy(sp, None, privacy, pv)
        return p2, mo2, w

    if mode == "advanced":
        p = entry["provider"] or default_p
        m_route = entry["model"]
        eff_mo: str | None = m_route if m_route else model_override
        p2, mo2, w = apply_privacy_policy(p, eff_mo, privacy, pv)
        return p2, mo2, w

    # single — optional per-task override (model / model_stack applies even when provider is primary)
    p = str(entry.get("provider") or "").strip()
    m_route = str(entry.get("model") or "").strip()
    if not p:
        eff_mo = m_route if m_route else model_override
        p2, mo2, w = apply_privacy_policy(req_p, eff_mo, privacy, pv)
        return p2, mo2, w
    eff_mo = m_route if m_route else model_override
    p2, mo2, w = apply_privacy_policy(p, eff_mo, privacy, pv)
    return p2, mo2, w


def build_routing_preview(workspace_root: Path, *, overlay: dict[str, Any] | None = None) -> dict[str, Any]:
    from lenses.llm_studio_tasks import STUDIO_TASK_DEFINITIONS

    base = llm_settings_store.load_raw(workspace_root)
    raw = merge_routing_preview_overlay(base, overlay) if overlay else base
    pv = providers_with_store(workspace_root)
    connected = sum(1 for x in pv.values() if x)
    rows: list[dict[str, Any]] = []
    default_p = str(raw.get("provider") or "openai").strip() or "openai"
    mode = str(raw.get("routing_mode") or "single").strip().lower()
    if mode not in ("single", "smart", "advanced"):
        mode = "single"
    for tid, label in STUDIO_TASK_DEFINITIONS:
        ent = _task_route_entry(raw, tid)
        p, mo, p_warn = effective_provider_for_task(raw, tid, default_p, None, workspace_root=workspace_root)
        model_resolved, _, dbg = resolve_effective_model(
            p,
            workspace_root=workspace_root,
            model_override=mo,
            refine=False,
            user_message=".",
            settings_raw=raw,
        )
        explanation = ""
        if mode == "smart":
            _sp, explanation = smart_provider_for_task(tid, default_p, raw, pv)
        elif mode == "advanced":
            explanation = "advanced:primary_route" if ent["provider"] else "advanced:primary_workspace_default"
        else:
            explanation = "single:per_task_override" if ent["provider"] else "single:primary_provider"
        rows.append(
            {
                "task_id": tid,
                "label": label,
                "provider": p,
                "model": str(model_resolved or mo or ""),
                "routing": dbg.get("source"),
                "routing_mode": mode,
                "explanation": explanation,
                "privacy": ent["privacy"],
                "privacy_warn": p_warn,
                "fallback_provider": ent["fallback_provider"] or None,
                "fallback_model": ent["fallback_model"] or None,
            }
        )
    return {"ok": True, "rows": rows, "connected_providers": connected, "routing_mode": mode}
