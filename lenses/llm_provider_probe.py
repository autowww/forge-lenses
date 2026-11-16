"""Server-side model discovery for AI Setup (credentials never sent to the browser)."""

from __future__ import annotations

import urllib.parse
from pathlib import Path
from typing import Any

from lenses import llm_settings_store
from lenses.llm_completions import ollama_daemon_status
from lenses.llm_http import http_get_json
from lenses.llm_resolve import merged_secret_keys
from lenses.llm_settings_store import merged_openai_compat_base_url

_MAX_MODEL_IDS = 400


def _cap_model_list(ids: list[str]) -> list[str]:
    if len(ids) > _MAX_MODEL_IDS:
        return ids[:_MAX_MODEL_IDS]
    return ids


def _parse_openai_models(out: dict[str, Any]) -> list[str]:
    data = out.get("data")
    if not isinstance(data, list):
        return []
    ids: list[str] = []
    for row in data:
        if isinstance(row, dict):
            mid = str(row.get("id", "") or "").strip()
            if mid:
                ids.append(mid)
    ids.sort()
    return ids


def _parse_gemini_models(out: dict[str, Any]) -> list[str]:
    models = out.get("models")
    if not isinstance(models, list):
        return []
    ids: list[str] = []
    for row in models:
        if not isinstance(row, dict):
            continue
        name = str(row.get("name", "") or "").strip()
        if not name:
            continue
        methods = row.get("supportedGenerationMethods")
        if isinstance(methods, list) and len(methods) > 0 and "generateContent" not in methods:
            continue
        short = name.split("/")[-1] if "/" in name else name
        if short:
            ids.append(short)
    ids.sort()
    return ids


def _parse_anthropic_models(out: dict[str, Any]) -> list[str]:
    data = out.get("data")
    if not isinstance(data, list):
        return []
    ids: list[str] = []
    for row in data:
        if isinstance(row, dict):
            mid = str(row.get("id", "") or "").strip()
            if mid:
                ids.append(mid)
    ids.sort()
    return ids


def discover_models(
    workspace_root: Path | None,
    provider: str,
    *,
    compat_base_probe: str | None = None,
    compat_bearer_probe: str | None = None,
) -> dict[str, Any]:
    """Return ``{ok, models?, error?, detail?}`` using merged keys from workspace + env.

    For ``openai_compatible`` only: optional ``compat_base_probe`` / ``compat_bearer_probe`` let
    Studio probe a **draft** base URL or bearer token before saving settings (UI-only; same SSRF
    trust boundary as other loopback-gated LLM APIs).
    """
    pid = (provider or "").strip().lower()
    if pid == "ollama":
        st = ollama_daemon_status()
        if not st.get("configured"):
            return {"ok": False, "error": "not_configured", "detail": "OLLAMA_BASE_URL"}
        if not st.get("reachable"):
            return {"ok": False, "error": "unreachable", "detail": str(st.get("base") or "")}
        models = st.get("models") if isinstance(st.get("models"), list) else []
        return {"ok": True, "models": _cap_model_list([str(m) for m in models if str(m).strip()])}

    if workspace_root is None:
        return {"ok": False, "error": "no_workspace", "detail": "workspace_root required"}

    raw = llm_settings_store.load_raw(workspace_root)
    keys = merged_secret_keys(raw)

    if pid == "openai":
        key = keys.get("openai", "").strip()
        if not key:
            return {"ok": False, "error": "not_configured", "detail": "OPENAI_API_KEY"}
        out = http_get_json(
            "https://api.openai.com/v1/models",
            {"Authorization": f"Bearer {key}"},
        )
        if out.get("_transport_error"):
            return {"ok": False, "error": "transport", "detail": str(out["_transport_error"])[:500]}
        err = out.get("error")
        if isinstance(err, dict):
            return {"ok": False, "error": "provider", "detail": str(err.get("message", "error"))[:500]}
        return {"ok": True, "models": _cap_model_list(_parse_openai_models(out))}

    if pid == "anthropic":
        key = keys.get("anthropic", "").strip()
        if not key:
            return {"ok": False, "error": "not_configured", "detail": "ANTHROPIC_API_KEY"}
        out = http_get_json(
            "https://api.anthropic.com/v1/models",
            {
                "x-api-key": key,
                "anthropic-version": "2023-06-01",
            },
        )
        if out.get("_transport_error"):
            return {"ok": False, "error": "transport", "detail": str(out["_transport_error"])[:500]}
        err = out.get("error")
        if isinstance(err, dict):
            return {"ok": False, "error": "provider", "detail": str(err.get("message", "error"))[:500]}
        models = _parse_anthropic_models(out)
        if not models and isinstance(out.get("data"), list) and len(out["data"]) == 0:
            return {"ok": True, "models": [], "detail": "empty_catalog"}
        return {"ok": True, "models": _cap_model_list(models)}

    if pid == "gemini":
        key = keys.get("gemini", "").strip()
        if not key:
            return {"ok": False, "error": "not_configured", "detail": "GOOGLE_API_KEY or GEMINI_API_KEY"}
        url = "https://generativelanguage.googleapis.com/v1beta/models?" + urllib.parse.urlencode({"key": key})
        out = http_get_json(url, {})
        if out.get("_transport_error"):
            return {"ok": False, "error": "transport", "detail": str(out["_transport_error"])[:500]}
        err = out.get("error")
        if isinstance(err, dict):
            return {"ok": False, "error": "provider", "detail": str(err.get("message", "error"))[:500]}
        return {"ok": True, "models": _cap_model_list(_parse_gemini_models(out))}

    if pid == "openai_compatible":
        merged_base = merged_openai_compat_base_url(raw).rstrip("/")
        base = merged_base
        if compat_base_probe is not None:
            pb = str(compat_base_probe).strip().rstrip("/")
            if pb:
                base = pb
        if not base:
            return {"ok": False, "error": "not_configured", "detail": "base_url"}
        if compat_bearer_probe is not None:
            key = str(compat_bearer_probe).strip()
        else:
            key = keys.get("openai_compatible", "").strip()
        hdrs: dict[str, str] = {}
        if key:
            hdrs["Authorization"] = f"Bearer {key}"
        url = f"{base}/v1/models"
        out = http_get_json(url, hdrs)
        if out.get("_transport_error"):
            return {"ok": False, "error": "transport", "detail": str(out["_transport_error"])[:500]}
        err = out.get("error")
        if isinstance(err, dict):
            return {"ok": False, "error": "provider", "detail": str(err.get("message", "error"))[:500]}
        return {"ok": True, "models": _cap_model_list(_parse_openai_models(out))}

    return {"ok": False, "error": "unknown_provider", "detail": pid}


def health_ping(
    workspace_root: Path | None,
    provider: str,
    *,
    compat_base_probe: str | None = None,
    compat_bearer_probe: str | None = None,
) -> dict[str, Any]:
    """Lightweight reachability: reuse model list where possible."""
    out = discover_models(
        workspace_root,
        provider,
        compat_base_probe=compat_base_probe,
        compat_bearer_probe=compat_bearer_probe,
    )
    if out.get("ok"):
        models = out.get("models")
        n = len(models) if isinstance(models, list) else 0
        return {"ok": True, "healthy": True, "model_count": n}
    return {"ok": True, "healthy": False, "error": out.get("error"), "detail": out.get("detail")}
