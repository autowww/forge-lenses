"""Pure helpers for KPI period totals, medians, and trend tiers (Studio overview)."""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from statistics import median
from typing import Any


def utc_today() -> date:
    return datetime.now(timezone.utc).date()


def period_start_end(today: date, window_days: int, k: int) -> tuple[date, date]:
    """Period k: k=0 is current window ending *today*; k=1 is the prior window, etc."""
    d = max(1, int(window_days))
    end_k = today - timedelta(days=k * d)
    start_k = end_k - timedelta(days=d - 1)
    return start_k, end_k


def sum_period_from_day_map(
    merged: dict[str, int],
    today: date,
    window_days: int,
    k: int,
) -> int:
    start_k, end_k = period_start_end(today, window_days, k)
    d = start_k
    s = 0
    while d <= end_k:
        s += int(merged.get(d.isoformat(), 0))
        d += timedelta(days=1)
    return s


def period_totals_seven_oldest_first(
    merged: dict[str, int],
    today: date,
    window_days: int,
) -> list[int]:
    """Seven period totals: index 0 = oldest (k=6), index 6 = current (k=0)."""
    return [
        sum_period_from_day_map(merged, today, window_days, k) for k in range(6, -1, -1)
    ]


def median_prior_six(period_totals_oldest_first: list[int]) -> float | None:
    """Median of the six periods before the current (first six entries when oldest-first)."""
    if len(period_totals_oldest_first) != 7:
        return None
    prior = period_totals_oldest_first[:6]
    return float(median(prior))


def trend_tier(current: int, med: float | None) -> str:
    """
    Green: current > median. Amber: current <= median but current >= 0.8 * median.
    Red: current < 0.8 * median. Unknown: insufficient median.
    If median == 0: green if current > 0, else amber at 0.
    """
    if med is None:
        return "unknown"
    if med == 0:
        return "green" if current > 0 else "amber"
    if current > med:
        return "green"
    if current >= 0.8 * med:
        return "amber"
    return "red"


def cumulative_daily_from_commit_series(
    daily_series: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """[{day, count}, ...] -> [{day, cumulative}, ...] for sparklines."""
    cum = 0
    out: list[dict[str, Any]] = []
    for row in daily_series:
        day = row.get("day")
        c = int(row.get("count") or 0)
        cum += c
        out.append({"day": day, "cumulative": cum})
    return out


def merge_day_maps(maps: list[dict[str, int]]) -> dict[str, int]:
    merged: dict[str, int] = {}
    for m in maps:
        for k, v in m.items():
            merged[k] = merged.get(k, 0) + int(v)
    return merged
