"""JSON payloads for Forge data charts (API + client-side rendering)."""

from __future__ import annotations

from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any

from lenses.project_stats import (
    collect_project_stats,
    commits_by_day_dict,
    overview_repo_row_metrics,
    workspace_commits_daily_series,
)
from lenses.repo_strategy import parse_gitmodules, svg_submodule_layout_svg


def _child_by_name(state: dict[str, Any], project_name: str) -> dict[str, Any] | None:
    for c in state.get("children") or []:
        if isinstance(c, dict) and str(c.get("name", "")) == project_name:
            return c
    return None


def build_project_chart_payload(
    repo_path: Path,
    state: dict[str, Any],
    project_name: str,
) -> dict[str, Any]:
    """Serializable chart bundle for `GET /api/project/<name>/chart-data`."""
    out: dict[str, Any] = {
        "version": 1,
        "scope": "project",
        "project": project_name,
        "charts": {},
    }
    if not (repo_path / ".git").exists():
        out["error"] = "not_git"
        return out

    stats = collect_project_stats(repo_path)
    weekly = [{"week": w["week"], "count": int(w["count"])} for w in (stats.get("commits_by_week") or [])]
    day_map = commits_by_day_dict(repo_path, 7)
    daily_pairs = workspace_commits_daily_series([day_map], days=7)
    daily = [{"day": d, "count": int(c)} for d, c in daily_pairs]

    child = _child_by_name(state, project_name) or {}
    sc = child.get("standards_compliance") if isinstance(child, dict) else None
    compliance_rows: list[list[Any]] = []
    if isinstance(sc, dict) and sc.get("score") is not None:
        compliance_rows.append([project_name, int(sc.get("score") or 0)])

    modules = parse_gitmodules(repo_path)
    paths = [str(m.get("path") or "") for m in modules if m.get("path")]
    sub_svg = svg_submodule_layout_svg(project_name, paths) if paths else ""

    ext_rows = [(str(x["extension"]), int(x["count"])) for x in (stats.get("extensions") or [])]
    total_tf = int(stats.get("tracked_files") or 0)

    out["charts"] = {
        "commit_weekly": {"series": weekly},
        "commit_daily": {"series": daily},
        "contributors": {"rows": [[str(x["commits"]), str(x["name"])] for x in (stats.get("contributors") or [])]},
        "extension_heatmap": {"extensions": ext_rows, "tracked_files": total_tf},
        "compliance_bars": {"rows": compliance_rows},
        "submodule_layout": {
            "project_label": project_name,
            "paths": paths,
            "svg_fragment": sub_svg,
        },
        "stats_raw": stats,
    }
    return out


def build_overview_chart_payload(state: dict[str, Any]) -> dict[str, Any]:
    """Workspace-level chart bundle for `GET /api/chart-data/overview`."""
    children: list[dict[str, Any]] = [
        c for c in (state.get("children") or []) if isinstance(c, dict)
    ]
    sorted_children = sorted(children, key=lambda ch: str(ch.get("name", "")).lower())
    max_workers = min(12, max(1, len(sorted_children)))
    rows_data: list[Any] = []
    if sorted_children:
        with ThreadPoolExecutor(max_workers=max_workers) as pool:
            rows_data = list(pool.map(overview_repo_row_metrics, sorted_children))

    loc_chart_rows: list[tuple[str, int]] = []
    loc_total_rows: list[tuple[str, int]] = []
    day_maps: list[dict[str, int]] = []
    agg_ext: Counter[str] = Counter()
    workspace_tracked_files = 0

    for row in rows_data:
        name, _path, _c, _commits, add_del, loc, day_dict, (ext_rows, ext_total) = row
        day_maps.append(day_dict)
        workspace_tracked_files += ext_total
        for ext, cnt in ext_rows:
            agg_ext[ext] += cnt
        if loc is not None:
            loc_total_rows.append((name, int(loc)))
        if add_del is not None:
            a, _d = add_del
            loc_chart_rows.append((name, int(a)))

    loc_chart_rows.sort(key=lambda x: -x[1])
    loc_chart_rows = loc_chart_rows[:40]
    loc_total_sorted = sorted(loc_total_rows, key=lambda x: -x[1])[:40]

    daily_series = workspace_commits_daily_series(day_maps, days=7)
    daily = [{"day": d, "count": int(c)} for d, c in daily_series]

    ext_top = sorted(agg_ext.items(), key=lambda x: -x[1])[:15]
    ext_denom = workspace_tracked_files if workspace_tracked_files > 0 else max(1, sum(agg_ext.values()))

    score_rows: list[list[Any]] = []
    for c in sorted_children:
        sc = c.get("standards_compliance")
        if isinstance(sc, dict) and "score" in sc:
            score_rows.append([str(c.get("name", "")), int(sc.get("score") or 0)])
    score_rows.sort(key=lambda x: -x[1])

    return {
        "version": 1,
        "scope": "overview",
        "charts": {
            "commit_daily": {"series": daily},
            "loc_added_horizontal": {
                "rows": [{"name": a, "value": b} for a, b in loc_chart_rows],
            },
            "loc_total_bars": {
                "rows": [{"name": a, "value": b} for a, b in loc_total_sorted],
            },
            "loc_share_donut": {
                "rows": [{"name": a, "value": b} for a, b in loc_total_rows],
                "top_n": 8,
            },
            "compliance_bars": {"rows": score_rows},
            "extension_heatmap": {
                "extensions": ext_top,
                "tracked_files": ext_denom,
            },
        },
    }
