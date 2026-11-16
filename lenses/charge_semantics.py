"""Shared Charge.md status heuristics (terminal, banked, blocked hints)."""

from __future__ import annotations

import re
from typing import Any

# Finished / closed — excluded from "active today" counts and bucketed as resolved.
CHARGE_TERMINAL_STATUSES = frozenset(
    {
        "done",
        "complete",
        "completed",
        "closed",
        "shipped",
        "cancelled",
        "canceled",
        "resolved",
        "wontfix",
        "wont fix",
        "duplicate",
    }
)

# Parked / deferred — not in-flight; separate from terminal in Today view.
CHARGE_BANKED_STATUSES = frozenset(
    {
        "banked",
        "parked",
        "deferred",
        "on hold",
        "on-hold",
        "waiting",
    }
)


def _norm_status(st: str) -> str:
    return re.sub(r"\s+", " ", (st or "").strip().lower())


def status_terminal(st: str) -> bool:
    """True when Charge status means the spark is finished or dropped."""
    s = _norm_status(st)
    if not s:
        return False
    if s in CHARGE_TERMINAL_STATUSES:
        return True
    return any(s.startswith(p) for p in ("done", "complete", "closed", "cancel"))


def status_banked(st: str) -> bool:
    """True when status indicates parked / banked work (not terminal)."""
    s = _norm_status(st)
    if not s or status_terminal(st):
        return False
    if s in CHARGE_BANKED_STATUSES:
        return True
    return any(
        s.startswith(p) for p in ("bank", "park", "defer", "on hold", "on-hold")
    )


def status_blocked_word(st: str) -> bool:
    """True when the status text suggests blocked (complements WBS / Blockers table)."""
    s = _norm_status(st)
    return "block" in s or s in ("stuck", "waiting on", "dependency")


def charge_active_today_count(charge_rows: list[dict[str, Any]]) -> int:
    """Rows in Active Sparks that still need attention (not terminal status)."""
    n = 0
    for row in charge_rows:
        if not status_terminal(str(row.get("status") or "")):
            n += 1
    return n
