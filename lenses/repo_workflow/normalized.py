"""Normalized workflow v1 shape (provider-agnostic)."""

from __future__ import annotations

from typing import Any

SCHEMA_VERSION = 1

# Top-level keys after adapter normalization (documentation + validation helpers)
WORKFLOW_V1_KEYS = frozenset(
    {
        "repository",
        "branches",
        "pull_requests",
        "commits_recent",
        "branch_protection",
        "code_owners",
        "reviews_summary",
    }
)


def empty_workflow_v1() -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "repository": {},
        "branches": [],
        "pull_requests": [],
        "commits_recent": [],
        "branch_protection": [],
        "code_owners": {},
        "reviews_summary": {},
    }


def compute_health(workflow: dict[str, Any]) -> dict[str, Any]:
    """Derive portfolio-style health counts from normalized PR/MR rows."""
    prs = workflow.get("pull_requests") if isinstance(workflow.get("pull_requests"), list) else []
    open_prs = [p for p in prs if isinstance(p, dict) and str(p.get("state") or "").lower() == "open"]
    stale = 0
    blocked = 0
    review_debt = 0
    for p in open_prs:
        try:
            sd = float(p.get("stale_days") or 0)
        except (TypeError, ValueError):
            sd = 0.0
        if sd >= 7:
            stale += 1
        m = str(p.get("mergeable") or "").lower()
        if m in ("conflicting", "false") or (p.get("merge_blocked_reason") or "").strip():
            blocked += 1
        try:
            review_debt += int(p.get("review_debt_count") or 0)
        except (TypeError, ValueError):
            pass
    rs = workflow.get("reviews_summary") if isinstance(workflow.get("reviews_summary"), dict) else {}
    return {
        "open_prs_count": len(open_prs),
        "stale_open_prs_count": stale,
        "blocked_merge_count": blocked,
        "review_debt_total": review_debt,
        "approved_open_count": int(rs.get("approved_open_count") or 0),
        "changes_requested_open_count": int(rs.get("changes_requested_open_count") or 0),
    }
