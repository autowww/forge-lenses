"""Aggregate plan spines for roadmap × WBS matrix (Studio roadmap matrix view)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from lenses.forge_spine import build_plan_spine_payload
from lenses.roadmap_outline import extract_date_shift_model

# Caps to keep large workspaces responsive (pair = one roadmap × WBS spine build).
MAX_ROADMAPS = 25
MAX_SPINE_PAIRS = 96
MAX_STORIES_PER_WBS_CELL = 48

_MILESTONE_SEP = "\x1f"


def _safe_wbs_file(workspace_root: Path, rel: str) -> Path | None:
    if not rel or ".." in rel.split("/") or rel.startswith(("/", "\\")):
        return None
    rel_norm = rel.replace("\\", "/").strip("/")
    candidate = (workspace_root / rel_norm).resolve()
    wr = workspace_root.resolve()
    try:
        candidate.relative_to(wr)
    except ValueError:
        return None
    parts = candidate.parts
    if "requirements" not in parts:
        return None
    if candidate.name != "WBS.md":
        return None
    if not candidate.is_file():
        return None
    return candidate


def _safe_roadmap_file(workspace_root: Path, rel: str) -> Path | None:
    if not rel or ".." in rel.split("/") or rel.startswith(("/", "\\")):
        return None
    rel_norm = rel.replace("\\", "/").strip("/")
    candidate = (workspace_root / rel_norm).resolve()
    wr = workspace_root.resolve()
    try:
        candidate.relative_to(wr)
    except ValueError:
        return None
    parts = candidate.parts
    if "docs" not in parts:
        return None
    if candidate.name != "ROADMAP.md":
        return None
    if not candidate.is_file():
        return None
    return candidate


def milestone_norm_key(ms: dict[str, Any]) -> str:
    ek = str(ms.get("epic_key") or "")
    t = str(ms.get("title") or "")
    return f"{ek}{_MILESTONE_SEP}{t}"


def _iso_to_month(iso: str | None) -> str | None:
    if not iso or len(iso) < 7:
        return None
    return iso[:7]


def _epic_month_map_from_roadmap_md(md: str) -> dict[str, str]:
    """Map epic id (from date-shift table) to YYYY-MM bucket."""
    ds = extract_date_shift_model(md)
    out: dict[str, str] = {}
    for row in ds.get("rows") or []:
        if not isinstance(row, dict):
            continue
        eid = str(row.get("epic_id") or "").strip()
        if not eid:
            continue
        t_s = row.get("target_start") or row.get("initial_start")
        if not t_s:
            continue
        ym = _iso_to_month(str(t_s) if t_s else None)
        if ym:
            out[eid] = ym
    return out


def _month_bucket_for_milestone(
    epic_key: str,
    epic_to_month: dict[str, str],
) -> str:
    ek = (epic_key or "").strip()
    if ek and ek in epic_to_month:
        return epic_to_month[ek]
    # Loose match: date-shift epic id may be a substring of WBS epic key
    for eid, ym in epic_to_month.items():
        if eid and (eid in ek or ek in eid):
            return ym
    return "unscheduled"


def aggregate_milestone_rows_for_roadmap(
    workspace_root: Path,
    *,
    repo_hint: str,
    roadmap_rel: str,
    wbs_rel_list: list[str],
    epic_to_month: dict[str, str],
    pairs_budget: int,
    spine_fn: Any,
) -> tuple[list[dict[str, Any]], int, bool]:
    """
    Build spine per WBS × roadmap and merge milestones.

    ``spine_fn`` defaults to ``build_plan_spine_payload``; injectable for tests.

    Returns (milestone rows, pairs_used, truncated).
    """
    fn = spine_fn or build_plan_spine_payload
    merged: dict[str, dict[str, Any]] = {}
    pairs_used = 0
    truncated = False

    for wbs_rel in wbs_rel_list:
        if pairs_used >= pairs_budget:
            truncated = True
            break
        if _safe_wbs_file(workspace_root, wbs_rel) is None:
            continue
        if _safe_roadmap_file(workspace_root, roadmap_rel) is None:
            continue
        pairs_used += 1
        spine = fn(
            workspace_root,
            repo_hint=repo_hint,
            wbs_rel=wbs_rel,
            roadmap_rel=roadmap_rel or None,
        )
        if not spine.get("ok"):
            continue
        plan = spine.get("plan") or {}
        milestones = plan.get("milestones") or []
        for ms in milestones:
            if not isinstance(ms, dict):
                continue
            stories_raw = ms.get("stories") or []
            if not stories_raw:
                continue
            key = milestone_norm_key(ms)
            ek = str(ms.get("epic_key") or "")
            title = str(ms.get("title") or "")
            theme = str(ms.get("theme") or "")
            month_bucket = _month_bucket_for_milestone(ek, epic_to_month)

            if key not in merged:
                merged[key] = {
                    "milestone_key": key,
                    "epic_key": ek,
                    "title": title,
                    "theme": theme,
                    "month_bucket": month_bucket,
                    "by_wbs": {},
                    "_seen_ids": set(),
                }
            row = merged[key]
            # Month: earliest scheduled wins if multiple spines disagree
            if month_bucket != "unscheduled":
                cur = row.get("month_bucket")
                if cur == "unscheduled" or (
                    isinstance(cur, str) and cur > month_bucket
                ):
                    row["month_bucket"] = month_bucket

            bucket_stories: list[dict[str, Any]] = []
            for st in stories_raw:
                if not isinstance(st, dict):
                    continue
                sid = str(st.get("id") or "").strip()
                if not sid:
                    continue
                row["_seen_ids"].add(sid)
                bucket_stories.append(
                    {
                        "id": sid,
                        "title": str(st.get("title") or ""),
                        "task_count": int(st.get("task_count") or 0),
                    }
                )
            if not bucket_stories:
                continue
            capped = bucket_stories[:MAX_STORIES_PER_WBS_CELL]
            row["by_wbs"][wbs_rel] = {
                "story_count": len(capped),
                "stories": capped,
            }

    out_rows: list[dict[str, Any]] = []
    for _k, row in sorted(merged.items(), key=lambda kv: kv[0]):
        seen: set[str] = row.pop("_seen_ids")
        by_wbs = row["by_wbs"]
        wbs_loaded_count = len(by_wbs)
        out_rows.append(
            {
                "milestone_key": row["milestone_key"],
                "epic_key": row["epic_key"],
                "title": row["title"],
                "theme": row["theme"],
                "month_bucket": row["month_bucket"],
                "wbs_loaded_count": wbs_loaded_count,
                "unique_story_count": len(seen),
                "by_wbs": by_wbs,
            }
        )
    return out_rows, pairs_used, truncated


def build_roadmaps_matrix_payload(
    workspace_root: Path,
    state: dict[str, Any],
    *,
    repo_filter: str,
) -> dict[str, Any]:
    """
    JSON for GET /api/roadmaps-matrix.

    ``repo_filter``: ``all`` or a ``repo_hint`` string matching scan rows.
    """
    wr = workspace_root.resolve()
    rf = (repo_filter or "all").strip()
    if not rf:
        rf = "all"

    wbs_rows: list[dict[str, Any]] = [
        w for w in (state.get("wbs") or []) if isinstance(w, dict)
    ]
    roadmap_rows: list[dict[str, Any]] = [
        r for r in (state.get("roadmaps") or []) if isinstance(r, dict)
    ]

    repo_options = sorted(
        {str(w.get("repo_hint") or "").strip() for w in wbs_rows if w.get("repo_hint")}
    )
    if rf != "all" and rf not in repo_options:
        return {
            "ok": False,
            "error": "unknown_repo_filter",
            "repo_filter": rf,
            "repo_options": repo_options,
        }

    if rf != "all":
        wbs_rows = [w for w in wbs_rows if str(w.get("repo_hint") or "") == rf]
        roadmap_rows = [r for r in roadmap_rows if str(r.get("repo_hint") or "") == rf]

    roadmap_rows = roadmap_rows[:MAX_ROADMAPS]

    global_pairs = 0
    out_roadmaps: list[dict[str, Any]] = []
    warnings: list[str] = []

    for rm in roadmap_rows:
        roadmap_rel = str(rm.get("rel_path") or "").strip()
        repo_hint = str(rm.get("repo_hint") or "").strip()
        if not roadmap_rel or not repo_hint:
            continue
        if _safe_roadmap_file(wr, roadmap_rel) is None:
            continue

        rm_path = wr / roadmap_rel.replace("\\", "/").strip("/")
        epic_to_month: dict[str, str] = {}
        try:
            md = rm_path.read_text(encoding="utf-8", errors="replace")
            epic_to_month = _epic_month_map_from_roadmap_md(md)
        except OSError:
            pass

        wbs_for_repo = [
            str(w.get("rel_path") or "").strip()
            for w in wbs_rows
            if str(w.get("repo_hint") or "") == repo_hint
        ]
        wbs_for_repo = [p for p in wbs_for_repo if p]

        budget = max(0, MAX_SPINE_PAIRS - global_pairs)
        if budget <= 0:
            warnings.append("roadmaps_matrix_pair_cap")
            out_roadmaps.append(
                {
                    "roadmap_rel": roadmap_rel,
                    "repo_hint": repo_hint,
                    "milestones": [],
                    "stats": {
                        "pairs_built": 0,
                        "pairs_cap": MAX_SPINE_PAIRS,
                        "truncated": True,
                    },
                }
            )
            continue

        milestones, pairs_used, truncated = aggregate_milestone_rows_for_roadmap(
            wr,
            repo_hint=repo_hint,
            roadmap_rel=roadmap_rel,
            wbs_rel_list=wbs_for_repo,
            epic_to_month=epic_to_month,
            pairs_budget=budget,
            spine_fn=build_plan_spine_payload,
        )
        global_pairs += pairs_used
        out_roadmaps.append(
            {
                "roadmap_rel": roadmap_rel,
                "repo_hint": repo_hint,
                "milestones": milestones,
                "stats": {
                    "pairs_built": pairs_used,
                    "pairs_cap": MAX_SPINE_PAIRS,
                    "truncated": truncated or global_pairs >= MAX_SPINE_PAIRS,
                },
            }
        )

    # Column order: sorted YYYY-MM then unscheduled
    months: set[str] = set()
    for rm in out_roadmaps:
        for ms in rm.get("milestones") or []:
            mb = str(ms.get("month_bucket") or "unscheduled")
            if mb != "unscheduled":
                months.add(mb)
    column_order = sorted(months) + (["unscheduled"] if any(
        str(ms.get("month_bucket") or "") == "unscheduled"
        for rm in out_roadmaps
        for ms in (rm.get("milestones") or [])
    ) else [])

    return {
        "ok": True,
        "repo_filter": rf,
        "repo_options": repo_options,
        "column_order": column_order,
        "roadmaps": out_roadmaps,
        "limits": {
            "max_roadmaps": MAX_ROADMAPS,
            "max_spine_pairs": MAX_SPINE_PAIRS,
            "max_stories_per_wbs_cell": MAX_STORIES_PER_WBS_CELL,
        },
        "warnings": warnings,
    }
