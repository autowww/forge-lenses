"""Local-first dispatch: resolve provider chain by model slot."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from lenses.llm_completions import ollama_daemon_status
from lenses.llm_resolve import merged_openai_compat_base_url, providers_with_store
from lenses.llm_settings_store import load_raw

from lenses.agent_runtime.capabilities import build_provider_endpoints, default_model_slots
from lenses.agent_runtime.endpoint_registry import normalize_slot_id
from lenses.agent_runtime.types import DispatchPolicy, DispatchStep, DispatchTrace, default_dispatch_policy

SLOT_TASK_FALLBACK: dict[str, str] = {
    "triage.small": "docs_health_enricher",
    "writer.medium": "docs_health_writer",
    "reviewer.high": "docs_health_reviewer",
    "external_writer": "docs_health_writer",
    "external_reviewer": "docs_health_reviewer",
}


def _slot_meta(slot: str) -> dict[str, Any] | None:
    sid = normalize_slot_id(slot)
    for s in default_model_slots():
        if s.get("id") == sid:
            return dict(s)
    return None


def _endpoint_health_for_adapter(workspace_root: Path, adapter: str) -> tuple[str | None, str | None]:
    for ep in build_provider_endpoints(workspace_root):
        if str(ep.get("adapter") or "") == adapter:
            return str(ep.get("id") or "") or None, str(ep.get("health") or "") or None
    return None, None


def provider_ready(workspace_root: Path, provider: str, raw: dict[str, Any]) -> tuple[bool, str]:
    pid = (provider or "").strip().lower()
    pv = providers_with_store(workspace_root)
    if pid == "ollama":
        st = ollama_daemon_status()
        if not st.get("configured"):
            return False, "ollama_not_configured"
        if not st.get("reachable"):
            return False, "ollama_unreachable"
        return True, "ok"
    if pid == "openai_compatible":
        base = merged_openai_compat_base_url(raw) or ""
        if not base.strip():
            return False, "compat_url_missing"
        return True, "ok"
    if pid in ("openai", "anthropic", "gemini"):
        if not pv.get(pid):
            return False, f"{pid}_not_configured"
        return True, "ok"
    return False, "unknown_provider"


def _default_cloud_provider(raw: dict[str, Any]) -> str:
    return str(raw.get("provider") or "openai").strip().lower() or "openai"


def plan_dispatch(workspace_root: Path, slot: str) -> tuple[list[str], DispatchTrace]:
    """Return ordered provider ids to try, plus an inspectable trace."""
    raw = load_raw(workspace_root)
    policy = default_dispatch_policy(raw)
    requested_slot = str(slot or "").strip()
    normalized = normalize_slot_id(requested_slot)
    meta = _slot_meta(normalized)
    studio_task_id = str(
        (meta or {}).get("studio_task_id") or SLOT_TASK_FALLBACK.get(normalized, "docs_health_enricher")
    )
    order_keywords = list((meta or {}).get("fallback_order") or ["ollama", "openai_compatible", "cloud_default"])

    steps: list[DispatchStep] = []
    chain: list[str] = []

    def add_step(provider: str, adapter: str, reason: str, *, skipped: bool = False, skip_detail: str | None = None) -> None:
        eid: str | None = None
        eh: str | None = None
        if not skipped:
            eid, eh = _endpoint_health_for_adapter(workspace_root, adapter)
        steps.append(
            {
                "provider": provider,
                "adapter": adapter,
                "reason": reason,
                "skipped": skipped,
                "skip_detail": skip_detail,
                "endpoint_id": eid,
                "endpoint_health": eh,
            }
        )

    cloud_default = _default_cloud_provider(raw)
    slot_is_external = str(normalized).startswith("external")

    for kw in order_keywords:
        if len(chain) >= int(policy.get("max_escalation_steps") or 4):
            break
        if kw == "ollama":
            if slot_is_external:
                add_step("ollama", "ollama", "skip_local_for_external_slot", skipped=True, skip_detail="external_slot")
                continue
            ok, detail = provider_ready(workspace_root, "ollama", raw)
            if ok:
                add_step("ollama", "ollama", "local_preferred")
                chain.append("ollama")
            else:
                add_step("ollama", "ollama", "local_unavailable", skipped=True, skip_detail=detail)
        elif kw == "openai_compatible":
            if not policy.get("allow_private_compat_url", True):
                add_step("openai_compatible", "openai_compatible", "policy_disabled", skipped=True, skip_detail="compat_disabled")
                continue
            ok, detail = provider_ready(workspace_root, "openai_compatible", raw)
            if ok:
                add_step("openai_compatible", "openai_compatible", "private_url_fallback")
                chain.append("openai_compatible")
            else:
                add_step(
                    "openai_compatible",
                    "openai_compatible",
                    "compat_unavailable",
                    skipped=True,
                    skip_detail=detail,
                )
        elif kw == "cloud_default":
            if not policy.get("allow_cloud_escalation", True):
                add_step(cloud_default, cloud_default, "cloud_escalation_disabled", skipped=True, skip_detail="policy")
                continue
            ok, detail = provider_ready(workspace_root, cloud_default, raw)
            if ok:
                add_step(cloud_default, cloud_default, "cloud_escalation")
                chain.append(cloud_default)
            else:
                add_step(cloud_default, cloud_default, "cloud_unavailable", skipped=True, skip_detail=detail)

    # De-dup chain while preserving order
    seen: set[str] = set()
    out_chain: list[str] = []
    for p in chain:
        if p not in seen:
            seen.add(p)
            out_chain.append(p)

    cap_id = str((meta or {}).get("capability_id") or normalized)
    trace: DispatchTrace = {
        "slot": normalized,
        "requested_slot": requested_slot,
        "capability_id": cap_id,
        "studio_task_id": studio_task_id,
        "policy": policy,
        "steps_evaluated": steps,
        "chosen_index": 0 if out_chain else None,
        "fallback_used": len(out_chain) > 1 or (len(out_chain) == 1 and out_chain[0] != "ollama"),
    }
    return out_chain, trace
