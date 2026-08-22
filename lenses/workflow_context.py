"""Compact workflow context for the Forge plan shell (metrics strip + API).

Heuristics are deterministic and documented inline; tune here rather than in the UI.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from lenses.charge_semantics import charge_active_today_count
from lenses.forge_spine import index_versona_sessions, parse_charge_sparks
from lenses.forge_work_model import ForgeWorkModel, build_forge_work_model
from lenses.roadmap_outline import (
    extract_chart_metrics,
    extract_date_shift_model,
    extract_gantt_model,
)


def _blocked_work_count(model: ForgeWorkModel) -> int:
    """Sparks (tasks) with at least one blocker string."""
    return sum(
        1
        for n in model.nodes.values()
        if n.kind == "spark" and bool(n.blockers)
    )


def _pending_decision_count(model: ForgeWorkModel) -> int:
    """Indexed Ember decision chunks (decisionRef nodes)."""
    return sum(1 for n in model.nodes.values() if n.kind == "decisionRef")


def _pending_versona_count(sessions: list[dict[str, Any]]) -> int:
    """Sessions without an ember_log_ref (discipline work not yet logged to Ember)."""
    n = 0
    for s in sessions:
        ref = s.get("ember_log_ref")
        if ref is None or (isinstance(ref, str) and not ref.strip()):
            n += 1
    return n


def _active_milestone_and_spark(
    model: ForgeWorkModel,
    roadmap_md: str | None,
) -> tuple[str, str]:
    """
    Short labels for the context strip.

    *active_milestone*: Prefer the first roadmap Gantt milestone column that still
    has an epic bar whose status is not terminal; else the first Gantt milestone id;
    else the first WBS-derived milestone id (M1, M2, …); else em dash.

    *product_spark*: Title of the first root milestone node tagged as product_spark
    layer in forge_work_model; else same as milestone id label when present.
    """
    active_milestone = "—"
    product_spark = "—"

    root_milestones = [
        model.nodes[rid]
        for rid in model.root_ids
        if rid in model.nodes and model.nodes[rid].kind == "milestone"
    ]
    if root_milestones:
        first = root_milestones[0]
        if (first.extra or {}).get("layer") == "product_spark":
            product_spark = first.title or first.id
        else:
            product_spark = first.title or first.id

    if roadmap_md:
        gantt = extract_gantt_model(roadmap_md)
        milestones: list[str] = list(gantt.get("milestones") or [])
        bars: list[dict[str, Any]] = list(gantt.get("bars") or [])
        if milestones:
            # Pick first milestone column that still has a non-done bar touching it.
            terminal_bar = re.compile(
                r"^(done|complete|closed|shipped|cancel)", re.I
            )

            def bar_active(b: dict[str, Any]) -> bool:
                st = str(b.get("status") or "")
                return not bool(terminal_bar.match(st.strip()))

            idx_hit: int | None = None
            for i, _mid in enumerate(milestones):
                for b in bars:
                    if not bar_active(b):
                        continue
                    start = int(b.get("start", -1))
                    end = int(b.get("end", -1))
                    if start <= i <= end:
                        idx_hit = i
                        break
                if idx_hit is not None:
                    break
            if idx_hit is not None:
                active_milestone = milestones[idx_hit]
            else:
                active_milestone = milestones[0]

    if active_milestone == "—" and model.root_ids:
        for rid in model.root_ids:
            n = model.nodes.get(rid)
            if n and n.kind == "milestone":
                active_milestone = n.id
                break

    return active_milestone, product_spark


def _iteration_label(roadmap_md: str | None) -> str | None:
    """
    Reserved: no first-class iteration field in lenses models yet.

    If the roadmap preamble or a section title matches ``Iteration N`` / ``Sprint N``,
    that string is returned; else None.
    """
    if not roadmap_md:
        return None
    m = re.search(
        r"(?im)^(#{2,4})\s*((?:iteration|sprint)\s+[^\n]+)$",
        roadmap_md[:8000],
    )
    if m:
        return m.group(2).strip()[:80]
    return None


def build_workflow_context_payload(
    workspace_root: Path,
    *,
    repo_hint: str,
    wbs_rel: str,
    roadmap_rel: str | None = None,
) -> dict[str, Any]:
    """
    JSON for GET /api/workflow-context (same query shape as /api/plan-spine).

    When WBS is missing or disallowed, returns ``ok: False`` with an error key.
    """
    wr = workspace_root.resolve()
    wbs_path = wr / wbs_rel.replace("\\", "/").strip("/")
    if not wbs_path.is_file():
        return {"ok": False, "error": "wbs_not_found", "wbs_rel": wbs_rel}

    roadmap_md: str | None = None
    if roadmap_rel:
        rp = wr / roadmap_rel.replace("\\", "/").strip("/")
        if rp.is_file():
            roadmap_md = rp.read_text(encoding="utf-8", errors="replace")

    model = build_forge_work_model(
        wr, repo_hint=repo_hint, wbs_rel=wbs_rel, roadmap_rel=roadmap_rel
    )

    base = wr / repo_hint if repo_hint else wr
    charge_path = base / "forge" / "charge.md"
    charge_rows: list[dict[str, Any]] = []
    if charge_path.is_file():
        charge_rows = parse_charge_sparks(
            charge_path.read_text(encoding="utf-8", errors="replace")
        )

    versona_root = base / "forge-logs" / "versona"
    sessions = index_versona_sessions(wr, versona_root)

    active_milestone, product_spark = _active_milestone_and_spark(model, roadmap_md)
    metrics = extract_chart_metrics(roadmap_md) if roadmap_md else {}
    date_shift = extract_date_shift_model(roadmap_md) if roadmap_md else {}

    ctx = {
        "active_milestone": active_milestone,
        "product_spark": product_spark,
        "iteration": _iteration_label(roadmap_md),
        "blocked_count": _blocked_work_count(model),
        "pending_decisions_count": _pending_decision_count(model),
        "pending_versona_sessions_count": _pending_versona_count(sessions),
        "charge_today_size": charge_active_today_count(charge_rows),
        "roadmap_metrics": metrics,
        "roadmap_date_shift": date_shift,
        "sources_present": dict(model.sources_present),
    }
    return {
        "ok": True,
        "repo_hint": repo_hint,
        "wbs_rel": wbs_rel,
        "roadmap_rel": roadmap_rel or "",
        "context": ctx,
    }
