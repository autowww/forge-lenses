"""Execute model calls through dispatch + ledger."""

from __future__ import annotations

import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from lenses.agent_runtime.dispatch import plan_dispatch, provider_ready
from lenses.agent_runtime.endpoint_registry import docs_health_slot_lookup_keys
from lenses.agent_runtime.ledger import append_model_call, merge_usage_into_session_file
from lenses.agent_runtime.types import ModelCallRecord
from lenses.llm_chat import chat
from lenses.llm_settings_store import load_raw


def _endpoint_health_for_adapter(workspace_root: Path, adapter: str) -> tuple[str | None, str | None]:
    from lenses.agent_runtime.capabilities import build_provider_endpoints

    for ep in build_provider_endpoints(workspace_root):
        if str(ep.get("adapter") or "") == adapter:
            return str(ep.get("id") or "") or None, str(ep.get("health") or "") or None
    return None, None


def _slot_explicit_provider(workspace_root: Path, slot: str) -> str | None:
    raw = load_raw(workspace_root)
    dd = raw.get("docs_health_slots") if isinstance(raw.get("docs_health_slots"), dict) else {}
    valid = frozenset({"anthropic", "openai", "gemini", "ollama", "openai_compatible"})
    for key in docs_health_slot_lookup_keys(slot):
        ep = str(dd.get(key, "") or "").strip().lower()
        if ep in valid:
            return ep
    return None


def call_for_slot(
    workspace_root: Path,
    *,
    slot: str,
    message: str,
    studio_task_id: str,
    refine: bool = False,
    session_id: str | None = None,
    project_slug: str | None = None,
    scan_run_id: str | None = None,
    cluster_id: str | None = None,
    agent_definition_id: str | None = None,
) -> dict[str, Any]:
    """
    Local-first multi-hop dispatch. Records each attempt to the token ledger (failed tries included).
    """
    chain, trace = plan_dispatch(workspace_root, slot)
    explicit = _slot_explicit_provider(workspace_root, slot)
    if explicit and explicit not in chain:
        raw = load_raw(workspace_root)
        ok, _ = provider_ready(workspace_root, explicit, raw)
        if ok:
            chain = [explicit] + [p for p in chain if p != explicit]
            eid, eh = _endpoint_health_for_adapter(workspace_root, explicit)
            trace["steps_evaluated"].insert(
                0,
                {
                    "provider": explicit,
                    "adapter": explicit,
                    "reason": "docs_health_slots_override",
                    "skipped": False,
                    "skip_detail": None,
                    "endpoint_id": eid,
                    "endpoint_health": eh,
                },
            )

    if not chain:
        out = {
            "ok": False,
            "error": "no_endpoint",
            "detail": "no_provider_ready",
            "agent_runtime": {
                "dispatch_trace": trace,
                "slot": str(trace.get("slot") or slot),
                "capability_id": trace.get("capability_id"),
                "requested_slot": trace.get("requested_slot"),
            },
        }
        return out

    last: dict[str, Any] | None = None
    for idx, provider in enumerate(chain):
        t0 = time.monotonic()
        res = chat(provider, message, workspace_root=workspace_root, refine=refine, studio_task_id=studio_task_id)
        elapsed_ms = int((time.monotonic() - t0) * 1000)
        usage = res.get("usage") if isinstance(res.get("usage"), dict) else {}
        pt = int(usage.get("prompt_tokens") or 0)
        ct = int(usage.get("completion_tokens") or 0)
        tt = int(usage.get("total_tokens") or 0)
        if tt == 0 and (pt or ct):
            tt = pt + ct
        est = bool(usage.get("estimated")) if "estimated" in usage else not (pt or ct)
        mode = "estimated" if est else "exact"
        mid = res.get("model") if res.get("ok") else None
        rec: ModelCallRecord = {
            "id": uuid.uuid4().hex[:20],
            "ts": datetime.now(timezone.utc).isoformat(),
            "endpoint_id": f"{provider}",
            "provider": provider,
            "adapter": provider,
            "model_slot": str(trace.get("slot") or slot),
            "studio_task_id": studio_task_id,
            "model_id": str(mid).strip() if mid else None,
            "input_tokens": pt,
            "output_tokens": ct,
            "total_tokens": tt,
            "token_counting_mode": mode,  # type: ignore[assignment]
            "elapsed_ms": elapsed_ms,
            "ok": bool(res.get("ok")),
            "session_id": session_id,
            "project_slug": project_slug,
            "scan_run_id": scan_run_id,
            "cluster_id": cluster_id,
            "agent_definition_id": agent_definition_id,
            "dispatch_trace": trace if idx == 0 else None,
        }
        append_model_call(workspace_root, rec)
        trace["chosen_index"] = idx
        last = res
        if res.get("ok"):
            if session_id:
                merge_usage_into_session_file(
                    workspace_root,
                    session_id,
                    {
                        "calls": 1,
                        "prompt_tokens": pt,
                        "completion_tokens": ct,
                        "total_tokens": tt,
                        "estimated": est,
                        "last_slot": str(trace.get("slot") or slot),
                        "last_endpoint": provider,
                    },
                )
            res = dict(res)
            res["agent_runtime"] = {
                "dispatch_trace": trace,
                "chosen_provider": provider,
                "slot": str(trace.get("slot") or slot),
                "capability_id": trace.get("capability_id"),
                "requested_slot": trace.get("requested_slot"),
                "ledger_record_id": rec.get("id"),
            }
            return res

    assert last is not None
    last = dict(last)
    last["agent_runtime"] = {
        "dispatch_trace": trace,
        "slot": str(trace.get("slot") or slot),
        "capability_id": trace.get("capability_id"),
        "requested_slot": trace.get("requested_slot"),
        "chain_exhausted": True,
    }
    return last
