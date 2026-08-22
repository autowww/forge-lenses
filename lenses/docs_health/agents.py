"""LLM-backed docs agents (local-first via agent runtime dispatcher)."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from lenses.agent_runtime.endpoint_registry import (
    CAPABILITY_REVIEWER_HIGH,
    CAPABILITY_TRIAGE_SMALL,
    CAPABILITY_WRITER_MEDIUM,
)
from lenses.agent_runtime.invoke import call_for_slot

SLOT_TO_TASK: dict[str, str] = {
    CAPABILITY_TRIAGE_SMALL: "docs_health_enricher",
    CAPABILITY_WRITER_MEDIUM: "docs_health_writer",
    CAPABILITY_REVIEWER_HIGH: "docs_health_reviewer",
    "external_writer": "docs_health_writer",
    "external_reviewer": "docs_health_reviewer",
}

# Specialist studio_task_id values (routing / ledger); never embed vendor model IDs here.
TASK_CLUSTER = "docs_health_cluster"
TASK_DIAGRAM = "docs_health_diagram"
TASK_DECISION = "docs_health_decision"


def accumulate_usage(sess_usage: dict[str, Any], res: dict[str, Any], *, slot: str, endpoint: str) -> None:
    u = res.get("usage") if isinstance(res.get("usage"), dict) else {}
    pt = int(u.get("prompt_tokens") or 0)
    ct = int(u.get("completion_tokens") or 0)
    tt = int(u.get("total_tokens") or 0)
    if tt == 0 and (pt or ct):
        tt = pt + ct
    est = bool(u.get("estimated")) if "estimated" in u else not (pt or ct)
    sess_usage["calls"] = int(sess_usage.get("calls") or 0) + 1
    sess_usage["prompt_tokens"] = int(sess_usage.get("prompt_tokens") or 0) + pt
    sess_usage["completion_tokens"] = int(sess_usage.get("completion_tokens") or 0) + ct
    sess_usage["total_tokens"] = int(sess_usage.get("total_tokens") or 0) + tt
    sess_usage["estimated"] = bool(sess_usage.get("estimated")) or est
    sess_usage["last_slot"] = slot
    sess_usage["last_endpoint"] = endpoint
    ar = res.get("agent_runtime") if isinstance(res.get("agent_runtime"), dict) else {}
    if ar:
        traces = sess_usage.setdefault("dispatch_traces", [])
        if isinstance(traces, list):
            traces.append(ar.get("dispatch_trace"))
        sess_usage["last_chosen_provider"] = ar.get("chosen_provider")
        mid = res.get("model")
        if mid:
            sess_usage["last_model_id"] = str(mid).strip()
    by_slot = sess_usage.setdefault("by_slot", {})
    cur = by_slot.get(slot) if isinstance(by_slot.get(slot), dict) else {}
    cur_pt = int(cur.get("prompt_tokens") or 0) + pt
    cur_ct = int(cur.get("completion_tokens") or 0) + ct
    cur_tt = int(cur.get("total_tokens") or 0) + tt
    cur_calls = int(cur.get("calls") or 0) + 1
    by_slot[slot] = {
        "prompt_tokens": cur_pt,
        "completion_tokens": cur_ct,
        "total_tokens": cur_tt,
        "calls": cur_calls,
    }


def run_enricher(
    workspace_root: Path,
    *,
    project_name: str,
    cluster: dict[str, Any],
    findings: list[dict[str, Any]],
    sess_usage: dict[str, Any],
    runtime_session_id: str | None = None,
    scan_run_id: str | None = None,
    cluster_id: str | None = None,
) -> dict[str, Any]:
    slot = CAPABILITY_TRIAGE_SMALL
    tid = SLOT_TO_TASK[slot]
    body = json.dumps(
        {
            "project": project_name,
            "cluster": cluster,
            "findings": findings,
        },
        indent=2,
    )
    msg = (
        "You are a documentation health assistant. Explain the following cluster of findings in plain language "
        "for a busy engineering lead. Use short bullets. Do not propose code outside markdown documentation.\n\n"
        f"{body}"
    )
    res = call_for_slot(
        workspace_root,
        slot=slot,
        message=msg,
        studio_task_id=tid,
        session_id=runtime_session_id,
        project_slug=project_name,
        scan_run_id=scan_run_id,
        cluster_id=cluster_id,
        agent_definition_id="docs_health_remediation",
    )
    ep = str((res.get("agent_runtime") or {}).get("chosen_provider") or sess_usage.get("last_endpoint") or "ollama")
    accumulate_usage(sess_usage, res, slot=slot, endpoint=ep)
    return res


def run_cluster_agent(
    workspace_root: Path,
    *,
    project_name: str,
    cluster: dict[str, Any],
    findings: list[dict[str, Any]],
    sess_usage: dict[str, Any],
    runtime_session_id: str | None = None,
    scan_run_id: str | None = None,
    cluster_id: str | None = None,
) -> dict[str, Any]:
    """Cluster specialist: grouping narrative and remediation framing (local triage slot)."""
    slot = CAPABILITY_TRIAGE_SMALL
    body = json.dumps({"project": project_name, "cluster": cluster, "findings": findings}, indent=2)
    msg = (
        "You are the Cluster agent for documentation health. Summarize what this cluster is about, why findings "
        "belong together, and the safest documentation next steps. Use short sections: Scope, Why it matters, "
        "Recommended next step. Do not output code fences except plain markdown bullets.\n\n"
        f"{body}"
    )
    res = call_for_slot(
        workspace_root,
        slot=slot,
        message=msg,
        studio_task_id=TASK_CLUSTER,
        session_id=runtime_session_id,
        project_slug=project_name,
        scan_run_id=scan_run_id,
        cluster_id=cluster_id,
        agent_definition_id="docs_health_remediation",
    )
    ep = str((res.get("agent_runtime") or {}).get("chosen_provider") or sess_usage.get("last_endpoint") or "ollama")
    accumulate_usage(sess_usage, res, slot=slot, endpoint=ep)
    return res


def run_writer(
    workspace_root: Path,
    *,
    project_name: str,
    cluster: dict[str, Any],
    findings: list[dict[str, Any]],
    prior_summary: str,
    sess_usage: dict[str, Any],
    runtime_session_id: str | None = None,
    scan_run_id: str | None = None,
    cluster_id: str | None = None,
) -> dict[str, Any]:
    slot = CAPABILITY_WRITER_MEDIUM
    tid = SLOT_TO_TASK[slot]
    msg = (
        "Draft SAFE markdown documentation updates only. Output exactly one fenced block of type docs_patch "
        "containing JSON with keys: path (relative repo path), content (full new file text for that path). "
        "Only touch markdown (.md) files. Prefer minimal edits. If unsure, use a small new doc under docs/.\n\n"
        f"Project: {project_name}\nPrior summary:\n{prior_summary}\n\nFindings JSON:\n"
        + json.dumps({"cluster": cluster, "findings": findings}, indent=2)
    )
    res = call_for_slot(
        workspace_root,
        slot=slot,
        message=msg,
        studio_task_id=tid,
        session_id=runtime_session_id,
        project_slug=project_name,
        scan_run_id=scan_run_id,
        cluster_id=cluster_id,
        agent_definition_id="docs_health_remediation",
    )
    ep = str((res.get("agent_runtime") or {}).get("chosen_provider") or "ollama")
    accumulate_usage(sess_usage, res, slot=slot, endpoint=ep)
    return res


def run_diagram_agent(
    workspace_root: Path,
    *,
    project_name: str,
    cluster: dict[str, Any],
    findings: list[dict[str, Any]],
    prior_summary: str,
    sess_usage: dict[str, Any],
    runtime_session_id: str | None = None,
    scan_run_id: str | None = None,
    cluster_id: str | None = None,
) -> dict[str, Any]:
    """Diagram specialist: proposes a markdown file update containing a fenced Mermaid diagram (writer.medium slot)."""
    slot = CAPABILITY_WRITER_MEDIUM
    msg = (
        "You are the Diagram agent. Propose ONE markdown documentation update that adds or improves a Mermaid diagram "
        "inside a .md file. Prefer paths like docs/diagrams/<topic>.md or a small section in an existing doc. "
        "Output exactly one fenced block of type docs_patch containing JSON with keys: path (relative .md), "
        "content (full file text including ```mermaid ... ```). Only markdown files.\n\n"
        f"Project: {project_name}\nContext:\n{prior_summary}\n\nFindings JSON:\n"
        + json.dumps({"cluster": cluster, "findings": findings}, indent=2)
    )
    res = call_for_slot(
        workspace_root,
        slot=slot,
        message=msg,
        studio_task_id=TASK_DIAGRAM,
        session_id=runtime_session_id,
        project_slug=project_name,
        scan_run_id=scan_run_id,
        cluster_id=cluster_id,
        agent_definition_id="docs_health_remediation",
    )
    ep = str((res.get("agent_runtime") or {}).get("chosen_provider") or "ollama")
    accumulate_usage(sess_usage, res, slot=slot, endpoint=ep)
    return res


def run_decision_agent(
    workspace_root: Path,
    *,
    project_name: str,
    cluster: dict[str, Any],
    findings: list[dict[str, Any]],
    prior_summary: str,
    sess_usage: dict[str, Any],
    runtime_session_id: str | None = None,
    scan_run_id: str | None = None,
    cluster_id: str | None = None,
) -> dict[str, Any]:
    """Decision specialist: ADR / decision record stub (writer.medium slot)."""
    slot = CAPABILITY_WRITER_MEDIUM
    msg = (
        "You are the Decision agent. Draft ONE lightweight ADR-style markdown stub (status: proposed). "
        "Use path under docs/decisions/ or docs/adr/ when possible. "
        "Output exactly one fenced block of type docs_patch with JSON keys path and content only.\n\n"
        f"Project: {project_name}\nContext:\n{prior_summary}\n\nFindings JSON:\n"
        + json.dumps({"cluster": cluster, "findings": findings}, indent=2)
    )
    res = call_for_slot(
        workspace_root,
        slot=slot,
        message=msg,
        studio_task_id=TASK_DECISION,
        session_id=runtime_session_id,
        project_slug=project_name,
        scan_run_id=scan_run_id,
        cluster_id=cluster_id,
        agent_definition_id="docs_health_remediation",
    )
    ep = str((res.get("agent_runtime") or {}).get("chosen_provider") or "ollama")
    accumulate_usage(sess_usage, res, slot=slot, endpoint=ep)
    return res


def run_reviewer(
    workspace_root: Path,
    *,
    proposed: dict[str, str],
    sess_usage: dict[str, Any],
    runtime_session_id: str | None = None,
    project_slug: str | None = None,
    scan_run_id: str | None = None,
    cluster_id: str | None = None,
    contract_excerpt: str | None = None,
) -> dict[str, Any]:
    slot = CAPABILITY_REVIEWER_HIGH
    tid = SLOT_TO_TASK[slot]
    extra = ""
    if contract_excerpt and str(contract_excerpt).strip():
        extra = (
            "\n\nProject documentation contract (excerpt for alignment — do not quote secrets):\n"
            + str(contract_excerpt).strip()[:8000]
        )
    msg = (
        "Review the proposed markdown documentation patch for safety, contract alignment, clarity, and obvious "
        "hallucination or mismatch risk. Check fenced diagram syntax if present. "
        "Reply with JSON only: {\"approve\": true|false, \"notes\": \"...\"} — no markdown fences.\n\n"
        f"{json.dumps(proposed, indent=2)}"
        + extra
    )
    res = call_for_slot(
        workspace_root,
        slot=slot,
        message=msg,
        studio_task_id=tid,
        session_id=runtime_session_id,
        project_slug=project_slug,
        scan_run_id=scan_run_id,
        cluster_id=cluster_id,
        agent_definition_id="docs_health_remediation",
    )
    ep = str((res.get("agent_runtime") or {}).get("chosen_provider") or "ollama")
    accumulate_usage(sess_usage, res, slot=slot, endpoint=ep)
    return res


def parse_docs_patch(text: str) -> dict[str, str] | None:
    if not text:
        return None
    m = re.search(r"```docs_patch\s*([\s\S]*?)```", text, re.IGNORECASE)
    raw = m.group(1).strip() if m else text.strip()
    try:
        obj = json.loads(raw)
    except json.JSONDecodeError:
        return None
    if not isinstance(obj, dict):
        return None
    path = str(obj.get("path") or "").strip()
    content = str(obj.get("content") if obj.get("content") is not None else "")
    if not path or not path.endswith(".md"):
        return None
    return {"path": path, "content": content}


def parse_review_json(text: str) -> dict[str, Any] | None:
    t = (text or "").strip()
    if not t:
        return None
    try:
        obj = json.loads(t)
    except json.JSONDecodeError:
        # strip code fences if model added them
        m = re.search(r"\{[\s\S]*\}\s*$", t)
        if not m:
            return None
        try:
            obj = json.loads(m.group(0))
        except json.JSONDecodeError:
            return None
    return obj if isinstance(obj, dict) else None
