"""Append-only KPI snapshots under ``.lenses-local/kpi-history.json`` for snapshot metrics."""

from __future__ import annotations

import json
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

from lenses.kpi_trends import period_start_end

KPI_HISTORY_REL = Path(".lenses-local") / "kpi-history.json"
MAX_ENTRIES = 200


def _parse_resolved_iso(s: str | None) -> datetime | None:
    if not s or not isinstance(s, str):
        return None
    try:
        t = s.strip().replace("Z", "+00:00")
        return datetime.fromisoformat(t)
    except ValueError:
        return None


def append_kpi_snapshot(workspace_root: Path, state: dict[str, Any]) -> None:
    """Record current snapshot metrics after a workspace scan (best-effort, ignores I/O errors)."""
    wr = workspace_root.resolve()
    lens_dir = wr / ".lenses-local"
    try:
        lens_dir.mkdir(parents=True, exist_ok=True)
    except OSError:
        return

    children = [c for c in (state.get("children") or []) if isinstance(c, dict)]
    git_n = sum(1 for c in children if c.get("is_git"))
    sites = state.get("websites") or []
    sites_n = len(sites) if isinstance(sites, list) else 0
    wbs = state.get("wbs") or []
    roadmaps = state.get("roadmaps") or []
    wbs_n = len(wbs) if isinstance(wbs, list) else 0
    rm_n = len(roadmaps) if isinstance(roadmaps, list) else 0
    plan_n = wbs_n + rm_n

    scores: list[int] = []
    for c in children:
        sc = c.get("standards_compliance")
        if isinstance(sc, dict) and isinstance(sc.get("score"), (int, float)):
            scores.append(int(sc.get("score") or 0))
    compliance_avg: float | None
    if scores:
        compliance_avg = round(sum(scores) / len(scores), 2)
    else:
        compliance_avg = None

    entry = {
        "resolved_at": state.get("resolved_at") or "",
        "git_n": int(git_n),
        "sites_n": int(sites_n),
        "plan_n": int(plan_n),
        "compliance_avg": compliance_avg,
    }

    path = wr / KPI_HISTORY_REL
    data: dict[str, Any] = {"version": 1, "entries": []}
    if path.is_file():
        try:
            raw = path.read_text(encoding="utf-8", errors="replace")
            loaded = json.loads(raw)
            if isinstance(loaded, dict) and isinstance(loaded.get("entries"), list):
                data["entries"] = [e for e in loaded["entries"] if isinstance(e, dict)]
        except (OSError, json.JSONDecodeError):
            pass

    entries: list[dict[str, Any]] = data["entries"]
    # De-dupe: replace last entry if same resolved_at
    if entries and str(entries[-1].get("resolved_at", "")) == str(entry.get("resolved_at", "")):
        entries[-1] = entry
    else:
        entries.append(entry)
    if len(entries) > MAX_ENTRIES:
        data["entries"] = entries[-MAX_ENTRIES:]

    try:
        path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    except OSError:
        return


def load_kpi_snapshots(workspace_root: Path) -> list[dict[str, Any]]:
    path = workspace_root.resolve() / KPI_HISTORY_REL
    if not path.is_file():
        return []
    try:
        raw = path.read_text(encoding="utf-8", errors="replace")
        loaded = json.loads(raw)
        if not isinstance(loaded, dict):
            return []
        ent = loaded.get("entries")
        if not isinstance(ent, list):
            return []
        return [e for e in ent if isinstance(e, dict)]
    except (OSError, json.JSONDecodeError):
        return []


def _value_in_snapshot(entry: dict[str, Any], key: str) -> int | None:
    if key == "compliance_avg":
        v = entry.get("compliance_avg")
        if v is None:
            return None
        try:
            return int(round(float(v)))
        except (TypeError, ValueError):
            return None
    v = entry.get(key)
    if v is None:
        return None
    try:
        return int(v)
    except (TypeError, ValueError):
        return None


def snapshot_period_totals(
    entries: list[dict[str, Any]],
    today: date,
    window_days: int,
    key: str,
    current_live: int,
) -> list[int]:
    """
    Seven totals oldest-first using time buckets on ``resolved_at``.
    Current period (k=0) uses *current_live*; older periods use latest snapshot in each window.
    """
    d = max(1, int(window_days))
    out: list[int] = []
    for k in range(6, -1, -1):
        if k == 0:
            out.append(int(current_live))
            continue
        start_k, end_k = period_start_end(today, d, k)
        start_dt = datetime(
            start_k.year, start_k.month, start_k.day, tzinfo=timezone.utc
        )
        end_dt = datetime(
            end_k.year, end_k.month, end_k.day, 23, 59, 59, tzinfo=timezone.utc
        )
        best: dict[str, Any] | None = None
        best_t: datetime | None = None
        for e in entries:
            dt = _parse_resolved_iso(str(e.get("resolved_at") or ""))
            if dt is None:
                continue
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            dt = dt.astimezone(timezone.utc)
            if dt < start_dt or dt > end_dt:
                continue
            if best_t is None or dt > best_t:
                best_t = dt
                best = e
        if best is None:
            out.append(0)
        else:
            v = _value_in_snapshot(best, key)
            out.append(int(v) if v is not None else 0)

    return out


def median_from_prior_six(period_totals_oldest_first: list[int]) -> float | None:
    from statistics import median

    if len(period_totals_oldest_first) != 7:
        return None
    prior = period_totals_oldest_first[:6]
    if not prior:
        return None
    return float(median(prior))
