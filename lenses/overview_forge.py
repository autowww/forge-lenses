"""Workspace-level Forge execution rollup for the Overview page."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any

from lenses.roadmap_outline import extract_chart_metrics, extract_gantt_model
from lenses.today_charge_view import build_today_charge_payload, plan_href

_CAP_ACTIVE = 14
_CAP_BLOCKED = 10
_CAP_GAPS = 14
_CAP_WINDOWS = 8
_CAP_PROGRESS = 6
_MAX_WORKERS = 8


def _roadmaps_by_repo(state: dict[str, Any]) -> dict[str, list[str]]:
    out: dict[str, list[str]] = {}
    for r in state.get("roadmaps") or []:
        if not isinstance(r, dict):
            continue
        h = str(r.get("repo_hint", "")).strip()
        rp = str(r.get("rel_path", "")).strip()
        if not h or not rp:
            continue
        out.setdefault(h, []).append(rp)
    for k in out:
        out[k].sort()
    return out


def _forge_hint_order(state: dict[str, Any]) -> list[str]:
    order: list[str] = []
    for fh in state.get("forge_hints") or []:
        if not isinstance(fh, dict):
            continue
        h = str(fh.get("repo_hint", "")).strip()
        if h and h not in order:
            order.append(h)
    return order


def _md_wbs_entries(state: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for w in state.get("wbs") or []:
        if not isinstance(w, dict):
            continue
        rp = str(w.get("rel_path", "")).strip()
        if not rp.lower().endswith(".md"):
            continue
        rows.append(w)
    hint_order = _forge_hint_order(state)

    def sort_key(w: dict[str, Any]) -> tuple[int, str, str]:
        rh = str(w.get("repo_hint", "")).strip()
        pri = hint_order.index(rh) if rh in hint_order else 999
        return (pri, rh, rp)

    return sorted(rows, key=sort_key)


def _pick_roadmap(repo_hint: str, by_repo: dict[str, list[str]]) -> str | None:
    paths = by_repo.get(repo_hint) or []
    return paths[0] if paths else None


def _rollup_one(
    workspace_root: Path,
    wbs_row: dict[str, Any],
    roadmaps_by_repo: dict[str, list[str]],
) -> dict[str, Any]:
    repo_hint = str(wbs_row.get("repo_hint", "")).strip()
    wbs_rel = str(wbs_row.get("rel_path", "")).strip()
    roadmap_rel = _pick_roadmap(repo_hint, roadmaps_by_repo)

    payload = build_today_charge_payload(
        workspace_root,
        repo_hint=repo_hint,
        wbs_rel=wbs_rel,
        roadmap_rel=roadmap_rel,
    )

    windows: list[str] = []
    horizon_counts: dict[str, int] = {}
    epic_progress: list[tuple[str, float, str]] = []
    roadmap_rel_used = roadmap_rel or ""

    if roadmap_rel:
        rp = workspace_root / roadmap_rel.replace("\\", "/").strip("/")
        if rp.is_file():
            md = rp.read_text(encoding="utf-8", errors="replace")
            gm = extract_gantt_model(md)
            miles = gm.get("milestones") if isinstance(gm.get("milestones"), list) else []
            if isinstance(miles, list):
                windows = [str(m) for m in miles[:_CAP_WINDOWS]]
            metrics = extract_chart_metrics(md)
            hz = metrics.get("horizon_counts") if isinstance(metrics, dict) else {}
            if isinstance(hz, dict):
                horizon_counts = {str(k): int(v) for k, v in hz.items() if int(v) > 0}
            eb = metrics.get("epic_bars") or []
            if isinstance(eb, list):
                for item in eb[:_CAP_PROGRESS]:
                    if isinstance(item, (list, tuple)) and len(item) >= 2:
                        try:
                            pct = float(item[1])
                        except (TypeError, ValueError):
                            continue
                        epic_progress.append(
                            (str(item[0]), max(0.0, min(100.0, pct)), roadmap_rel_used)
                        )

    return {
        "repo_hint": repo_hint,
        "wbs_rel": wbs_rel,
        "roadmap_rel": roadmap_rel_used,
        "payload": payload,
        "windows": windows,
        "horizon_counts": horizon_counts,
        "epic_progress": epic_progress,
    }


def build_overview_forge_rollup(
    workspace_root: Path,
    state: dict[str, Any],
) -> dict[str, Any]:
    """
    Aggregate Forge signals across Markdown WBS files (parallel per repo/WBS).

    Returns structured JSON-like dict for HTML rendering: active sparks, blocked,
    evidence/decision gaps, upcoming milestone windows, lightweight progress.
    """
    wr = workspace_root.resolve()
    roadmaps_by_repo = _roadmaps_by_repo(state)
    entries = _md_wbs_entries(state)

    if not entries:
        return {
            "ok": True,
            "wbs_count": 0,
            "totals": {
                "active_sparks": 0,
                "blocked_sparks": 0,
                "spark_rows_with_gaps": 0,
            },
            "active_sparks": [],
            "blocked_sparks": [],
            "gaps": [],
            "upcoming_milestones": [],
            "horizon_totals": {},
            "progress_samples": [],
            "repos_touched": [],
        }

    rows_out: list[dict[str, Any]] = []
    max_workers = min(_MAX_WORKERS, max(1, len(entries)))

    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        futs = {
            pool.submit(_rollup_one, wr, w, roadmaps_by_repo): w for w in entries
        }
        for fut in as_completed(futs):
            try:
                rows_out.append(fut.result())
            except OSError:
                continue

    hint_order = _forge_hint_order(state)

    def _repo_sort_key(r: dict[str, Any]) -> tuple[int, str, str]:
        rh = str(r.get("repo_hint", "")).strip()
        pri = hint_order.index(rh) if rh in hint_order else 999
        return (pri, rh, str(r.get("wbs_rel", "")))

    rows_out.sort(key=_repo_sort_key)

    active_all: list[dict[str, Any]] = []
    blocked_all: list[dict[str, Any]] = []
    gaps_all: list[dict[str, Any]] = []
    horizon_merge: dict[str, int] = {}
    progress_samples: list[dict[str, Any]] = []
    seen_progress: set[str] = set()
    milestone_order: list[str] = []
    seen_m: set[str] = set()

    totals_active = 0
    totals_blocked = 0
    totals_gaps = 0
    repos_ok: list[str] = []

    for row in rows_out:
        payload = row["payload"]
        if not isinstance(payload, dict) or not payload.get("ok"):
            continue
        repos_ok.append(row["repo_hint"])
        sec = payload.get("sections") or {}
        wbs_rel = row["wbs_rel"]
        repo = row["repo_hint"]
        rm = row["roadmap_rel"] or None

        for sp in sec.get("active") or []:
            if not isinstance(sp, dict):
                continue
            totals_active += 1
            sid = str(sp.get("spark_id") or "")
            active_all.append(
                {
                    "spark_id": sid,
                    "title": str(sp.get("title") or sid),
                    "repo_hint": repo,
                    "wbs_rel": wbs_rel,
                    "status": str(sp.get("status") or ""),
                    "milestone": str((sp.get("forge_labels") or {}).get("milestone") or ""),
                    "plan_href": sp.get("plan_href")
                    or plan_href(wbs_rel, repo, rm, sid),
                }
            )

        for sp in sec.get("blocked") or []:
            if not isinstance(sp, dict):
                continue
            totals_blocked += 1
            sid = str(sp.get("spark_id") or "")
            blocked_all.append(
                {
                    "spark_id": sid,
                    "title": str(sp.get("title") or sid),
                    "repo_hint": repo,
                    "wbs_rel": wbs_rel,
                    "blocker": str(sp.get("blocker") or ""),
                    "plan_href": sp.get("plan_href")
                    or plan_href(wbs_rel, repo, rm, sid),
                }
            )

        for sp in payload.get("spark_rows") or []:
            if not isinstance(sp, dict):
                continue
            gaps = sp.get("gaps") or []
            if not gaps:
                continue
            totals_gaps += 1
            sid = str(sp.get("spark_id") or "")
            for g in gaps[:3]:
                if len(gaps_all) >= _CAP_GAPS * 2:
                    break
                gaps_all.append(
                    {
                        "spark_id": sid,
                        "title": str(sp.get("title") or sid),
                        "repo_hint": repo,
                        "gap": str(g),
                        "plan_href": sp.get("plan_href")
                        or plan_href(wbs_rel, repo, rm, sid),
                    }
                )

        hz = row.get("horizon_counts") or {}
        if isinstance(hz, dict):
            for k, v in hz.items():
                horizon_merge[k] = horizon_merge.get(k, 0) + int(v)

        for label, pct, _rm in row.get("epic_progress") or []:
            key = f"{repo}:{label}"
            if key in seen_progress:
                continue
            seen_progress.add(key)
            progress_samples.append(
                {
                    "label": label,
                    "pct": pct,
                    "repo_hint": repo,
                }
            )

        for m in row.get("windows") or []:
            sm = str(m).strip()
            if sm and sm not in seen_m:
                seen_m.add(sm)
                milestone_order.append(sm)

    active_sparks = active_all[:_CAP_ACTIVE]
    blocked_sparks = blocked_all[:_CAP_BLOCKED]
    gaps = gaps_all[:_CAP_GAPS]
    progress_samples = progress_samples[:_CAP_PROGRESS]

    upcoming = milestone_order[:_CAP_WINDOWS]

    return {
        "ok": True,
        "wbs_count": len(entries),
        "totals": {
            "active_sparks": totals_active,
            "blocked_sparks": totals_blocked,
            "spark_rows_with_gaps": totals_gaps,
        },
        "active_sparks": active_sparks,
        "blocked_sparks": blocked_sparks,
        "gaps": gaps,
        "upcoming_milestones": upcoming,
        "horizon_totals": horizon_merge,
        "progress_samples": progress_samples,
        "repos_touched": sorted(set(repos_ok)),
    }
