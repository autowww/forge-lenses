"""JSON payloads for Forge data charts (API + client-side rendering)."""

from __future__ import annotations

from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from pathlib import Path
from typing import Any

from lenses.kpi_history import load_kpi_snapshots, median_from_prior_six, snapshot_period_totals
from lenses.kpi_trends import (
    cumulative_daily_from_commit_series,
    median_prior_six,
    merge_day_maps,
    period_start_end,
    period_totals_seven_oldest_first,
    trend_tier,
    utc_today,
)
from lenses.project_stats import (
    collect_project_stats,
    commits_by_day_dict,
    commits_by_day_dict_range,
    git_numstat_between,
    git_numstat_since,
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


def horizon_query_days(horizon: str | None) -> int:
    """Map `horizon` query param (day|week|month|quarter) to a rolling day window for git."""
    h = (horizon or "").strip().lower()
    if h == "day":
        return 1
    if h == "month":
        return 30
    if h == "quarter":
        return 90
    return 7


def normalized_horizon_id(horizon: str | None) -> str:
    h = (horizon or "").strip().lower()
    if h in ("day", "month", "quarter", "week"):
        return h
    return "week"


def _avg_compliance(sorted_children: list[dict[str, Any]]) -> int | None:
    scores: list[int] = []
    for c in sorted_children:
        sc = c.get("standards_compliance")
        if isinstance(sc, dict) and isinstance(sc.get("score"), (int, float)):
            scores.append(int(sc.get("score") or 0))
    if not scores:
        return None
    return int(round(sum(scores) / len(scores)))


def build_overview_chart_payload(
    state: dict[str, Any],
    *,
    days: int = 7,
    horizon_id: str = "week",
) -> dict[str, Any]:
    """Workspace-level chart bundle for `GET /api/chart-data/overview`."""
    days = max(1, min(int(days), 366))
    hid = normalized_horizon_id(horizon_id)
    today = utc_today()
    span_days = min(7 * days, 630)
    oldest = today - timedelta(days=span_days - 1)

    children: list[dict[str, Any]] = [
        c for c in (state.get("children") or []) if isinstance(c, dict)
    ]
    sorted_children = sorted(children, key=lambda ch: str(ch.get("name", "")).lower())
    max_workers = min(12, max(1, len(sorted_children)))

    range_maps: dict[str, dict[str, int]] = {}
    for c in sorted_children:
        if not c.get("is_git"):
            continue
        name = str(c.get("name", ""))
        path = Path(str(c.get("path", "")))
        range_maps[name] = commits_by_day_dict_range(path, oldest, today)

    rows_data: list[Any] = []
    if sorted_children:

        def row_for_child(ch: dict[str, Any]) -> Any:
            nm = str(ch.get("name", ""))
            dm = range_maps.get(nm)
            return overview_repo_row_metrics(ch, days=days, day_dict=dm)

        with ThreadPoolExecutor(max_workers=max_workers) as pool:
            rows_data = list(pool.map(row_for_child, sorted_children))

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

    daily_series = workspace_commits_daily_series(day_maps, days=days)
    daily = [{"day": d, "count": int(c)} for d, c in daily_series]

    merged_commits = merge_day_maps(list(range_maps.values()))
    commit_period_totals = period_totals_seven_oldest_first(merged_commits, today, days)
    commit_median = median_prior_six(commit_period_totals)
    commit_current = commit_period_totals[-1] if commit_period_totals else 0
    commit_prev = commit_period_totals[-2] if len(commit_period_totals) >= 2 else 0
    cumulative_daily = cumulative_daily_from_commit_series(daily)

    git_children = [c for c in sorted_children if c.get("is_git")]
    per_repo_periods: dict[str, list[int]] = defaultdict(list)
    lines_period_totals: list[int] = []
    for k in range(6, -1, -1):
        sk, ek = period_start_end(today, days, k)

        def lines_pair(ch: dict[str, Any]) -> tuple[str, int]:
            p = Path(str(ch.get("path", "")))
            nm = str(ch.get("name", "")).strip()
            a, _b = git_numstat_between(p, sk, ek)
            return nm, int(a)

        if git_children:
            with ThreadPoolExecutor(max_workers=max_workers) as pool:
                pairs = list(pool.map(lines_pair, git_children))
            period_sum = 0
            for nm, add in pairs:
                per_repo_periods[nm].append(add)
                period_sum += add
            lines_period_totals.append(period_sum)
        else:
            lines_period_totals.append(0)

    # 1-day horizon: current period = rolling last 24h (git --since=1 days ago), same as loc chart rows.
    # Calendar single-day windows often show 0 when activity was "today local" but not UTC date.
    if days == 1 and git_children:

        def lines_since_24h(ch: dict[str, Any]) -> tuple[str, int]:
            p = Path(str(ch.get("path", "")))
            nm = str(ch.get("name", "")).strip()
            a, _b = git_numstat_since(p, 1)
            return nm, int(a)

        with ThreadPoolExecutor(max_workers=max_workers) as pool:
            since_pairs = list(pool.map(lines_since_24h, git_children))
        roll_sum = sum(a for _nm, a in since_pairs)
        if lines_period_totals:
            lines_period_totals[-1] = roll_sum
        for nm, a in since_pairs:
            pts = per_repo_periods.get(nm)
            if pts is not None and len(pts) == 7:
                pts[-1] = a

    per_repo_lines: dict[str, Any] = {}
    for nm, pts in per_repo_periods.items():
        if len(pts) != 7:
            continue
        pmed = median_prior_six(pts)
        pcur = int(pts[-1])
        per_repo_lines[nm] = {
            "period_totals": [int(x) for x in pts],
            "median_prior_6": pmed,
            "tier": trend_tier(pcur, pmed),
        }

    lines_median = median_prior_six(lines_period_totals)
    lines_current = lines_period_totals[-1] if lines_period_totals else 0
    lines_prev = lines_period_totals[-2] if len(lines_period_totals) >= 2 else 0

    lines_prev_by_repo: dict[str, int] = {}
    if git_children:
        s1, e1 = period_start_end(today, days, 1)

        def prev_lines(ch: dict[str, Any]) -> tuple[str, int]:
            p = Path(str(ch.get("path", "")))
            nm = str(ch.get("name", "")).strip()
            a, _b = git_numstat_between(p, s1, e1)
            return nm, int(a)

        with ThreadPoolExecutor(max_workers=max_workers) as pool:
            for nm, v in pool.map(prev_lines, git_children):
                lines_prev_by_repo[nm] = v

    wr = Path(str(state.get("workspace_root") or ".")).resolve()
    hist = load_kpi_snapshots(wr)
    git_n = sum(1 for c in sorted_children if c.get("is_git"))
    sites_n = len(state.get("websites") or []) if isinstance(state.get("websites"), list) else 0
    wbs_n = len(state.get("wbs") or []) if isinstance(state.get("wbs"), list) else 0
    rm_n = len(state.get("roadmaps") or []) if isinstance(state.get("roadmaps"), list) else 0
    plan_n = wbs_n + rm_n
    compliance_avg = _avg_compliance(sorted_children)

    snap_git = snapshot_period_totals(hist, today, days, "git_n", git_n)
    snap_sites = snapshot_period_totals(hist, today, days, "sites_n", sites_n)
    snap_plan = snapshot_period_totals(hist, today, days, "plan_n", plan_n)

    stand_live = int(compliance_avg) if compliance_avg is not None else 0
    snap_stand = snapshot_period_totals(
        hist, today, days, "compliance_avg", stand_live
    )
    med_git = median_from_prior_six(snap_git)
    med_sites = median_from_prior_six(snap_sites)
    med_plan = median_from_prior_six(snap_plan)
    med_stand = median_from_prior_six([int(x) for x in snap_stand]) if snap_stand else None

    kpi_trends: dict[str, Any] = {
        "commits": {
            "current_total": int(commit_current),
            "previous_total": int(commit_prev),
            "period_totals": [int(x) for x in commit_period_totals],
            "median_prior_6": commit_median,
            "tier": trend_tier(int(commit_current), commit_median),
            "cumulative_daily": cumulative_daily,
        },
        "lines_added": {
            "current_total": int(lines_current),
            "previous_total": int(lines_prev),
            "period_totals": [int(x) for x in lines_period_totals],
            "median_prior_6": lines_median,
            "tier": trend_tier(int(lines_current), lines_median),
            "prev_by_repo": lines_prev_by_repo,
            "per_repo_lines": per_repo_lines,
        },
        "snapshots": {
            "git_repos": {
                "current": int(git_n),
                "previous_total": int(snap_git[-2]) if len(snap_git) >= 2 else 0,
                "period_totals": [int(x) for x in snap_git],
                "median_prior_6": med_git,
                "tier": trend_tier(int(git_n), med_git),
                "history_entries": len(hist),
            },
            "sites": {
                "current": int(sites_n),
                "previous_total": int(snap_sites[-2]) if len(snap_sites) >= 2 else 0,
                "period_totals": [int(x) for x in snap_sites],
                "median_prior_6": med_sites,
                "tier": trend_tier(int(sites_n), med_sites),
                "history_entries": len(hist),
            },
            "plan_artifacts": {
                "current": int(plan_n),
                "previous_total": int(snap_plan[-2]) if len(snap_plan) >= 2 else 0,
                "period_totals": [int(x) for x in snap_plan],
                "median_prior_6": med_plan,
                "tier": trend_tier(int(plan_n), med_plan),
                "history_entries": len(hist),
            },
            "standards_avg": {
                "current": compliance_avg,
                "previous_total": float(snap_stand[-2]) if len(snap_stand) >= 2 else None,
                "period_totals": [float(x) for x in snap_stand],
                "median_prior_6": med_stand,
                "tier": (
                    trend_tier(stand_live, med_stand)
                    if compliance_avg is not None
                    else "unknown"
                ),
                "history_entries": len(hist),
            },
        },
    }

    ext_top = sorted(agg_ext.items(), key=lambda x: -x[1])[:15]
    ext_denom = workspace_tracked_files if workspace_tracked_files > 0 else max(1, sum(agg_ext.values()))

    score_rows: list[list[Any]] = []
    for c in sorted_children:
        sc = c.get("standards_compliance")
        if isinstance(sc, dict) and "score" in sc:
            score_rows.append([str(c.get("name", "")), int(sc.get("score") or 0)])
    score_rows.sort(key=lambda x: -x[1])

    return {
        "version": 2,
        "scope": "overview",
        "horizon": hid,
        "window_days": days,
        "kpi_trends": kpi_trends,
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
