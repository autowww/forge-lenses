"""Scope closure hints for Docs Health (bounded MVP — no autonomous loop)."""

from __future__ import annotations

from typing import Any


def _sev_rank(s: str) -> int:
    t = (s or "").strip().lower()
    return {"critical": 3, "major": 2, "minor": 1}.get(t, 0)


def overlay_finding_suppressions(
    findings: list[Any],
    *,
    suppressed_finding_ids: set[str],
    suppressed_cluster_ids: set[str],
    clusters: list[Any] | None,
) -> list[dict[str, Any]]:
    """Return findings as dicts with ``user_suppressed`` / ``suppression_scope`` when applicable."""
    cluster_to_suppressed: set[str] = set()
    if clusters:
        for c in clusters:
            if not isinstance(c, dict):
                continue
            cid = str(c.get("id") or "").strip()
            if cid and cid in suppressed_cluster_ids:
                for fid in c.get("finding_ids") or []:
                    cluster_to_suppressed.add(str(fid))

    out: list[dict[str, Any]] = []
    for f in findings or []:
        if not isinstance(f, dict):
            continue
        row = dict(f)
        fid = str(row.get("id") or "").strip()
        if fid and (fid in suppressed_finding_ids or fid in cluster_to_suppressed):
            row["user_suppressed"] = True
        out.append(row)
    return out


def compute_closure_status(
    findings: list[dict[str, Any]],
    *,
    work_items_open: int,
) -> dict[str, Any]:
    """
    Bounded "finish current scope" signal for Studio.

    ``complete`` is true when no critical/major findings remain that are not user-suppressed
    and not ticket-only/manual without a tracked open item (heuristic: we only gate on severity + suppression).
    """
    open_hard = 0
    open_manualish = 0
    suppressed_open = 0
    for f in findings:
        if not isinstance(f, dict):
            continue
        if f.get("suppressed") is True or f.get("user_suppressed") is True:
            suppressed_open += 1
            continue
        fx = str(f.get("fixability") or "").lower()
        sev = _sev_rank(str(f.get("severity") or ""))
        if sev >= 2:
            open_hard += 1
        if fx in ("ticket_only", "manual"):
            open_manualish += 1

    # MVP: "scope complete" when no unsuppressed critical/major remain.
    complete = open_hard == 0
    return {
        "complete": complete,
        "open_critical_or_major": open_hard,
        "suppressed_findings_in_view": suppressed_open,
        "open_manual_or_ticket_style": open_manualish,
        "open_docs_work_items": work_items_open,
        "notes": (
            "No unsuppressed critical/major findings in the latest scan."
            if complete
            else "Critical or major findings remain — continue in Master or ticket via KTLO."
        ),
    }
