"""Foundry run activity log — Cursor-style agent feed persisted on the run record."""

from __future__ import annotations

from typing import Any

from lenses.foundry.payload import normalize_phases
from lenses.foundry.store import _now_iso, load_run, save_run, touch_run

_PHASE_START: dict[str, str] = {
    "classify": "Classifying task (domain, size, risk)",
    "route": "Routing to autonomy tier",
    "context": "Building context pack from target repo",
    "plan": "Planning patch units and verification commands",
    "draft-unit": "Drafting patch with worker",
    "draft-unit-0": "Drafting patch with worker",
    "apply+verify": "Applying patch and running verification",
    "assay": "Running assay gate on proof evidence",
    "promote": "Promoting changed files",
}


def _phase_label(name: str) -> str:
    n = (name or "").strip()
    if n in _PHASE_START:
        return _PHASE_START[n]
    if n.startswith("draft-"):
        return "Drafting patch with worker"
    if n.startswith("repair-"):
        return "Repair loop — re-drafting after verification failure"
    return n.replace("-", " ").replace("_", " ").strip().title() or "Working"


def _tone_for_status(status: str) -> str:
    s = (status or "").strip().lower()
    if s in ("ok", "pass", "completed"):
        return "ok"
    if s in ("fail", "failed", "error"):
        return "err"
    if s in ("escalated", "blocked"):
        return "err"
    return "info"


def append_activity(
    workspace_root,
    run_id: str,
    *,
    text: str,
    tone: str = "info",
    phase: str = "",
) -> None:
    record = load_run(workspace_root, run_id)
    if not record:
        return
    activities: list[dict[str, Any]] = list(record.get("activity") or [])
    activities.append(
        {
            "id": f"act_{len(activities) + 1}",
            "ts": _now_iso(),
            "text": text.strip(),
            "tone": tone,
            "phase": phase,
        }
    )
    record = touch_run(record, activity=activities)
    save_run(workspace_root, record)


def sync_phase_progress(workspace_root, run_id: str, phase: Any) -> None:
    """Persist DF phase completion into activity + partial stage bar."""
    name = str(getattr(phase, "name", None) or (phase.get("name") if isinstance(phase, dict) else "") or "")
    status = str(getattr(phase, "status", None) or (phase.get("status") if isinstance(phase, dict) else "") or "")
    detail = str(getattr(phase, "detail", None) or (phase.get("detail") if isinstance(phase, dict) else "") or "")
    record = load_run(workspace_root, run_id)
    if not record:
        return

    label = _phase_label(name)
    tone = _tone_for_status(status)
    text = f"{label} — {detail}" if detail else f"{label} — {status or 'done'}"

    activities: list[dict[str, Any]] = list(record.get("activity") or [])
    activities.append(
        {
            "id": f"act_{len(activities) + 1}",
            "ts": _now_iso(),
            "text": text,
            "tone": tone,
            "phase": name,
        }
    )

    accum: list[dict[str, Any]] = list(record.get("df_phase_accum") or [])
    replaced = False
    for row in accum:
        if str(row.get("name") or "") == name:
            row["status"] = status
            row["detail"] = detail
            replaced = True
            break
    if not replaced:
        accum.append({"name": name, "status": status, "detail": detail})

    record = touch_run(
        record,
        activity=activities,
        df_phase_accum=accum,
        phases=normalize_phases(accum),
        current_phase=name,
    )
    save_run(workspace_root, record)


def bootstrap_run_activity(
    workspace_root,
    run_id: str,
    *,
    goal: str,
    worker: str,
    project: str,
) -> None:
    append_activity(
        workspace_root,
        run_id,
        text=f"Run queued — L1 draft for {project or 'target'}",
        tone="busy",
    )
    append_activity(
        workspace_root,
        run_id,
        text=f"Goal: {goal[:200]}",
        tone="info",
    )
    append_activity(
        workspace_root,
        run_id,
        text=f"Worker backend: {worker}",
        tone="info",
    )
    append_activity(
        workspace_root,
        run_id,
        text="Launching Dark Factory driver…",
        tone="busy",
        phase="classify",
    )
