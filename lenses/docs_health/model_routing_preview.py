"""Attach planned provider + configured model id hints for Docs Health session API views."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from lenses.agent_runtime.dispatch import plan_dispatch
from lenses.agent_runtime.endpoint_registry import (
    CAPABILITY_REVIEWER_HIGH,
    CAPABILITY_TRIAGE_SMALL,
    CAPABILITY_WRITER_MEDIUM,
)
from lenses.llm_settings_store import load_raw


def _main_model_for_provider(raw: dict[str, Any], provider: str | None) -> str:
    if not provider:
        return ""
    pid = str(provider).strip().lower()
    mm = raw.get("main_models") if isinstance(raw.get("main_models"), dict) else {}
    v = str(mm.get(pid) or "").strip()
    return v


def build_model_routing_preview(workspace_root: Path) -> dict[str, Any]:
    """
    For each Docs Health capability slot, compute the current dispatch chain and the
    **configured** main model id for the first available provider (from LLM settings).

    Does not call remote LLMs — only reads settings + local Ollama health.
    """
    root = Path(workspace_root)
    raw = load_raw(root)
    slots_out: dict[str, Any] = {}
    order: list[tuple[str, str]] = [
        (CAPABILITY_TRIAGE_SMALL, "Triage"),
        (CAPABILITY_WRITER_MEDIUM, "Writer"),
        (CAPABILITY_REVIEWER_HIGH, "Reviewer"),
    ]
    for slot_id, label in order:
        chain, trace = plan_dispatch(root, slot_id)
        primary = chain[0] if chain else None
        model = _main_model_for_provider(raw, primary)
        chain_models: list[dict[str, str]] = []
        for p in chain:
            mid = _main_model_for_provider(raw, p)
            chain_models.append({"provider": str(p), "model": mid or "—"})
        slots_out[slot_id] = {
            "label": label,
            "primary_provider": primary,
            "primary_model": model or "—",
            "provider_chain": [str(x) for x in chain],
            "chain_with_models": chain_models,
            "capability_id": trace.get("capability_id"),
            "requested_slot": trace.get("requested_slot"),
        }
    default = raw.get("provider") or "openai"
    return {
        "slots": slots_out,
        "default_cloud_provider": str(default).strip().lower() or "openai",
        "note": "Primary model is from LLM settings (main_models) for the first healthy provider in the chain.",
    }


def attach_model_routing_preview(workspace_root: Path | Any, view: dict[str, Any]) -> None:
    """Merge routing preview onto a session payload dict (mutates in place)."""
    view["model_routing_preview"] = build_model_routing_preview(Path(workspace_root))
