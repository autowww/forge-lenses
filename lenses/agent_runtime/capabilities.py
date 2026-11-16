"""Provider endpoints and model slots with capability metadata."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from lenses.llm_completions import ollama_daemon_status
from lenses.llm_resolve import merged_openai_compat_base_url, merged_secret_keys, providers_with_store
from lenses.llm_settings_store import load_raw

from lenses.agent_runtime.types import ModelSlot, ProviderEndpoint


def _ollama_endpoint() -> ProviderEndpoint:
    st = ollama_daemon_status()
    cfg = bool(st.get("configured"))
    ok = bool(st.get("reachable"))
    if not cfg:
        health: str = "not_configured"
    elif ok:
        health = "healthy"
    else:
        health = "unavailable"
    models = st.get("models") if isinstance(st.get("models"), list) else []
    mc = min(131072, 32000 + len(models) * 100)  # coarse hint for UI
    return {
        "id": "ollama_local",
        "adapter": "ollama",
        "display_name": "Ollama (local)",
        "base_url_hint": str(st.get("base") or ""),
        "supports_text": cfg and ok,
        "supports_streaming": cfg and ok,
        "max_context_tokens": mc,
        "json_mode_reliable": False,
        "health": health,  # type: ignore[typeddict-item]
        "token_counting": "estimated",
        "privacy": "local_only",
        "cost_tier": "free",
        "latency_tier": "local_low",
        "last_probe_error": None if ok else "daemon_unreachable",
        "served_capabilities": [
            "triage.small",
            "writer.medium",
            "reviewer.high",
        ],
    }


def _openai_compat_endpoint(workspace_root: Path, raw: dict[str, Any]) -> ProviderEndpoint:
    base = merged_openai_compat_base_url(raw) or ""
    keys = merged_secret_keys(raw)
    bearer = str(keys.get("openai_compatible_bearer") or keys.get("openai_compat_bearer") or "").strip()
    configured = bool(base)
    health: str = "healthy" if configured else "not_configured"
    return {
        "id": "openai_compatible_url",
        "adapter": "openai_compatible",
        "display_name": "OpenAI-compatible URL",
        "base_url_hint": base[:80] + ("…" if len(base) > 80 else ""),
        "supports_text": configured,
        "supports_streaming": configured,
        "max_context_tokens": 128000,
        "json_mode_reliable": bool(configured and bearer),
        "health": health,  # type: ignore[typeddict-item]
        "token_counting": "exact",
        "privacy": "private_url",
        "cost_tier": "low",
        "latency_tier": "network_variable",
        "last_probe_error": None,
        "served_capabilities": ["writer.medium", "reviewer.high", "triage.small"],
    }


def _cloud_endpoint(pid: str, label: str, privacy: str) -> ProviderEndpoint:
    return {
        "id": f"cloud_{pid}",
        "adapter": pid,
        "display_name": label,
        "base_url_hint": "",
        "supports_text": True,
        "supports_streaming": True,
        "max_context_tokens": 200000 if pid == "anthropic" else 128000,
        "json_mode_reliable": pid != "ollama",
        "health": "not_configured",
        "token_counting": "exact",
        "privacy": privacy,  # type: ignore[typeddict-item]
        "cost_tier": "medium",
        "latency_tier": "cloud",
        "served_capabilities": ["triage.small", "writer.medium", "reviewer.high"],
    }


def build_provider_endpoints(workspace_root: Path) -> list[ProviderEndpoint]:
    raw = load_raw(workspace_root)
    pv = providers_with_store(workspace_root)
    out: list[ProviderEndpoint] = [_ollama_endpoint(), _openai_compat_endpoint(workspace_root, raw)]
    for pid, label in (
        ("openai", "OpenAI"),
        ("anthropic", "Anthropic"),
        ("gemini", "Gemini"),
    ):
        ep = _cloud_endpoint(pid, label, "cloud_allowed")
        ep["health"] = "healthy" if pv.get(pid) else "not_configured"  # type: ignore[assignment]
        out.append(ep)
    return out


def default_model_slots() -> list[ModelSlot]:
    """
    Canonical capability slots (``triage.small``, …). Legacy ``local_*`` ids are accepted via
    :func:`lenses.agent_runtime.endpoint_registry.normalize_slot_id` in the dispatcher.
    """
    local_order = ["ollama", "openai_compatible", "cloud_default"]
    return [
        {
            "id": "triage.small",
            "capability_id": "triage.small",
            "label": "Triage (small)",
            "studio_task_id": "docs_health_enricher",
            "preferred_privacy": "local_only",
            "primary_endpoint_kind": "local",
            "fallback_order": list(local_order),
        },
        {
            "id": "writer.medium",
            "capability_id": "writer.medium",
            "label": "Writer (medium)",
            "studio_task_id": "docs_health_writer",
            "preferred_privacy": "local_only",
            "primary_endpoint_kind": "local",
            "fallback_order": list(local_order),
        },
        {
            "id": "reviewer.high",
            "capability_id": "reviewer.high",
            "label": "Reviewer (high)",
            "studio_task_id": "docs_health_reviewer",
            "preferred_privacy": "local_only",
            "primary_endpoint_kind": "local",
            "fallback_order": list(local_order),
        },
        {
            "id": "external_writer",
            "capability_id": "writer.medium",
            "label": "External writer (private URL)",
            "studio_task_id": "docs_health_writer",
            "preferred_privacy": "private_url",
            "primary_endpoint_kind": "external_url",
            "fallback_order": ["openai_compatible", "cloud_default"],
        },
        {
            "id": "external_reviewer",
            "capability_id": "reviewer.high",
            "label": "External reviewer (private URL)",
            "studio_task_id": "docs_health_reviewer",
            "preferred_privacy": "private_url",
            "primary_endpoint_kind": "external_url",
            "fallback_order": ["openai_compatible", "cloud_default"],
        },
    ]


def build_routing_policy_summary(workspace_root: Path) -> dict[str, Any]:
    from lenses.agent_runtime.types import default_dispatch_policy

    raw = load_raw(workspace_root)
    pol = default_dispatch_policy(raw)
    mode = str(raw.get("routing_mode") or "single").strip().lower()
    from lenses.agent_runtime.endpoint_registry import default_endpoint_capabilities

    caps = default_endpoint_capabilities()
    return {
        "dispatch_policy": pol,
        "llm_routing_mode": mode,
        "slots": [s["id"] for s in default_model_slots()],
        "capability_ids": [c["id"] for c in caps],
        "summary": (
            f"local_first={pol.get('local_first')}; cloud_escalation={pol.get('allow_cloud_escalation')}; "
            f"compat_url={pol.get('allow_private_compat_url')}; llm_mode={mode}"
        ),
    }
