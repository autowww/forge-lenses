"""JSON payload for Enterprise Timeline (mirrors ``page_timeline`` selectors and roadmap slice)."""

from __future__ import annotations

from pathlib import Path
import sqlite3

LENSES_ROOT = Path(__file__).resolve().parent.parent
from typing import Any

from lenses.roadmap_charts import (
    horizon_badges_html,
    roadmap_date_shift_html,
    roadmap_gantt_html,
    svg_epic_progress_bars,
)
from lenses.roadmap_outline import (
    extract_chart_metrics,
    extract_date_shift_model,
    extract_gantt_model,
)
from lenses.render import (
    _repo_hints_wbs_then_roadmaps,
    roadmap_date_editor_fragment,
    workspace_project_for_repo,
    workspace_project_names_sorted,
)
from lenses.safe_forge_paths import roadmap_timeline_view_link


def build_timeline_api_payload(
    workspace_root: Path,
    state: dict[str, Any],
    query: dict[str, list[str]],
    *,
    orchestration_conn: sqlite3.Connection | None = None,
) -> dict[str, Any]:
    """Return selector options and HTML fragments for the /timeline Enterprise view."""
    wbs_rows = [w for w in (state.get("wbs") or []) if isinstance(w, dict)]
    rms = [r for r in (state.get("roadmaps") or []) if isinstance(r, dict)]
    valid_wbs = {str(w.get("rel_path", "")) for w in wbs_rows if str(w.get("rel_path", "")).strip()}
    valid_rm = {str(r.get("rel_path", "")) for r in rms if str(r.get("rel_path", "")).strip()}

    repo_q = (query.get("repo") or [""])[0].strip()
    wbs_q = (query.get("wbs_p") or [""])[0].strip()
    rm_q = (query.get("roadmap_p") or [""])[0].strip()

    if wbs_q not in valid_wbs and wbs_rows:
        wbs_q = str(wbs_rows[0].get("rel_path", "")).strip()
    if wbs_q:
        for w in wbs_rows:
            if str(w.get("rel_path", "")).strip() == wbs_q:
                repo_q = str(w.get("repo_hint", "")).strip()
                break
    if not repo_q and wbs_rows:
        repo_q = str(wbs_rows[0].get("repo_hint", "")).strip()
        wbs_q = str(wbs_rows[0].get("rel_path", "")).strip()
    if not repo_q and rms:
        repo_q = str(rms[0].get("repo_hint", "")).strip()

    rms_for_repo = [
        str(r.get("rel_path", "")).strip()
        for r in rms
        if str(r.get("repo_hint", "")).strip() == repo_q
    ]
    if rm_q not in valid_rm or (rms_for_repo and rm_q not in rms_for_repo):
        rm_q = rms_for_repo[0] if rms_for_repo else ""

    wp = workspace_project_names_sorted(state)
    scope = workspace_project_for_repo(repo_q, wp)

    repo_hints = _repo_hints_wbs_then_roadmaps(wbs_rows, rms)

    wbs_options = [
        {
            "rel_path": str(w.get("rel_path", "")).strip(),
            "repo_hint": str(w.get("repo_hint", "")).strip(),
        }
        for w in wbs_rows
        if str(w.get("rel_path", "")).strip()
    ]
    roadmap_options = [
        {
            "rel_path": str(r.get("rel_path", "")).strip(),
            "repo_hint": str(r.get("repo_hint", "")).strip(),
        }
        for r in rms
        if str(r.get("rel_path", "")).strip()
    ]

    gantt_html = ""
    metrics_row_html = ""
    editor_html = ""
    src_link = ""
    if rm_q:
        rpth = workspace_root / rm_q.replace("\\", "/").strip("/")
        if rpth.is_file():
            md = rpth.read_text(encoding="utf-8", errors="replace")
            gm = extract_gantt_model(md)
            gh = roadmap_gantt_html(gm, heading=True)
            dsm = extract_date_shift_model(md)
            dsh = roadmap_date_shift_html(dsm, heading=True)
            if gh or dsh:
                gantt_html = f"{gh or ''}{dsh or ''}"
            else:
                gantt_html = (
                    '<p class="forge-support">No Gantt slice or Initial/Target dates found. Use '
                    "milestone tables plus epics with <code>M#.#</code> in the Horizon column, "
                    "and/or optional ISO date columns per <code>ROADMAP.template.md</code>.</p>"
                )
            met = extract_chart_metrics(md)
            hz_html = horizon_badges_html(met.get("horizon_counts") or {})
            epic_pairs: list[tuple[str, float]] = []
            for item in met.get("epic_bars") or []:
                if isinstance(item, (list, tuple)) and len(item) >= 2:
                    try:
                        epic_pairs.append((str(item[0]), float(item[1])))
                    except (TypeError, ValueError):
                        continue
            prog = svg_epic_progress_bars(epic_pairs, width=720) if epic_pairs else ""
            if hz_html or prog:
                metrics_row_html = (
                    '<div class="lenses-timeline-metrics row g-3 mt-3">'
                    f'<div class="col-12">{hz_html}</div>'
                    f'<div class="col-12">{prog}</div>'
                    "</div>"
                )
            src_link = roadmap_timeline_view_link(rm_q)
            editor_html = roadmap_date_editor_fragment(LENSES_ROOT, rm_q, md, include_script=False)

    out: dict[str, Any] = {
        "ok": True,
        "repo_hints": repo_hints,
        "wbs_options": wbs_options,
        "roadmap_options": roadmap_options,
        "selected": {
            "repo": repo_q,
            "wbs_p": wbs_q,
            "roadmap_p": rm_q,
        },
        "workspace_projects": wp,
        "current_project": scope,
        "gantt_html": gantt_html,
        "metrics_html": metrics_row_html,
        "roadmap_source_href": src_link,
        "editor_html": editor_html,
    }
    if orchestration_conn is not None:
        from lenses.orchestration_graph.portfolio import build_timeline_portfolio_overlay

        out["orchestration_portfolio"] = build_timeline_portfolio_overlay(orchestration_conn)
    return out
