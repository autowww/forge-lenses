"""
Deterministic recheck status report for Blueprints Wizard (experimental).

Primary label precedence per slice (highest first):
missing → blocked → conflicting → stale → draft → approved → present
"""

from __future__ import annotations

from collections import defaultdict, deque
from datetime import datetime, timezone
from typing import Any

from lenses.blueprints_wizard.artifact_generation_dependencies import (
    ARTIFACT_UPSTREAM_AND,
    ARTIFACT_UPSTREAM_ONE_OF,
    EXECUTION_SLICE_KEYS,
    ENGINEERING_SLICE_KEYS,
    OWNERSHIP_REQUIRES_ANY_OF,
    PLANNING_SLICE_KEYS,
    QA_VERIFICATION_REQUIRES_ANY_OF,
    ROLLOUT_NOTES_REQUIRES_ANY_OF,
    assert_upstream_approved,
)
from lenses.blueprints_wizard.artifact_generation_normalize import ARTIFACT_SLICE_KEYS, QUALITY_DIMENSIONS
from lenses.blueprints_wizard.artifact_lineage_drift import (
    is_sealed_conflict,
    lineage_drift_detail_for_slice,
)
from lenses.blueprints_wizard.artifact_generation_dependencies import _approved as record_approved

PRIMARY_LABELS = (
    "missing",
    "blocked",
    "conflicting",
    "stale",
    "draft",
    "approved",
    "present",
)

# Higher = worse (for bucket aggregation).
SEVERITY_RANK: dict[str, int] = {
    "present": 0,
    "approved": 1,
    "draft": 2,
    "stale": 3,
    "conflicting": 4,
    "blocked": 5,
    "missing": 6,
}

MIN_QUALITY_SCORE = 0.5


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _content_nonempty(rec: dict[str, Any]) -> bool:
    c = rec.get("content")
    if not isinstance(c, dict):
        return False
    if len(c) == 0:
        return False
    for v in c.values():
        if v is None:
            continue
        if isinstance(v, str) and v.strip():
            return True
        if isinstance(v, list) and len(v) > 0:
            return True
        if isinstance(v, dict) and len(v) > 0:
            return True
    return False


def _quality_failures(rec: dict[str, Any]) -> list[str]:
    reasons: list[str] = []
    q = rec.get("quality")
    if not isinstance(q, dict):
        reasons.append("quality_missing")
        return reasons
    for dim in QUALITY_DIMENSIONS:
        entry = q.get(dim)
        if not isinstance(entry, dict):
            reasons.append(f"quality:{dim}:missing")
            continue
        try:
            score = float(entry.get("score", 0))
        except (TypeError, ValueError):
            score = 0.0
        if score < MIN_QUALITY_SCORE:
            reasons.append(f"quality:{dim}:below_threshold")
    return reasons


def _reverse_downstream_edges() -> dict[str, set[str]]:
    """Map upstream key -> set of downstream keys that depend on it."""
    rev: dict[str, set[str]] = defaultdict(set)
    for dk, ups in ARTIFACT_UPSTREAM_AND.items():
        for u in ups:
            rev[u].add(dk)
    for dk, groups in ARTIFACT_UPSTREAM_ONE_OF.items():
        for group in groups:
            for u in group:
                rev[u].add(dk)
    return dict(rev)


_REVERSE_DOWNSTREAM = _reverse_downstream_edges()


def transitive_downstream(seed_keys: frozenset[str]) -> list[str]:
    """All keys in ``seed_keys`` plus transitive downstream dependents (sorted)."""
    if not seed_keys:
        return []
    seen: set[str] = set(seed_keys)
    q: deque[str] = deque(sorted(seed_keys))
    while q:
        k = q.popleft()
        for d in sorted(_REVERSE_DOWNSTREAM.get(k, ())):
            if d not in seen:
                seen.add(d)
                q.append(d)
    return sorted(seen)


def list_blocking_upstream_keys(ak: str, arts: dict[str, Any]) -> list[str]:
    """Upstream keys that are not satisfied for ``ak`` (deterministic order)."""
    inflight = frozenset({ak})

    def _ready(k: str) -> bool:
        if k in inflight:
            return True
        return record_approved(arts.get(k))

    out: list[str] = []
    if ak in ARTIFACT_UPSTREAM_AND:
        for uk in ARTIFACT_UPSTREAM_AND[ak]:
            if not _ready(uk):
                out.append(uk)
    if ak in ARTIFACT_UPSTREAM_ONE_OF:
        groups = ARTIFACT_UPSTREAM_ONE_OF[ak]
        if not any(all(_ready(k) for k in group) for group in groups):
            for group in groups:
                for k in group:
                    if not _ready(k) and k not in out:
                        out.append(k)
    if ak == "ownership_review_matrix":
        if not any(_ready(k) for k in OWNERSHIP_REQUIRES_ANY_OF):
            for k in OWNERSHIP_REQUIRES_ANY_OF:
                if not _ready(k) and k not in out:
                    out.append(k)
    if ak == "qa_verification_checklist":
        if not any(_ready(k) for k in QA_VERIFICATION_REQUIRES_ANY_OF):
            for k in QA_VERIFICATION_REQUIRES_ANY_OF:
                if not _ready(k) and k not in out:
                    out.append(k)
    if ak == "rollout_notes":
        if not any(_ready(k) for k in ROLLOUT_NOTES_REQUIRES_ANY_OF):
            for k in ROLLOUT_NOTES_REQUIRES_ANY_OF:
                if not _ready(k) and k not in out:
                    out.append(k)
    return out


def _bucket_for_key(key: str) -> str:
    if key in PLANNING_SLICE_KEYS:
        return "planning"
    if key in ENGINEERING_SLICE_KEYS:
        return "engineering"
    if key in EXECUTION_SLICE_KEYS:
        return "execution"
    return "unknown"


def _inspect_row(key: str, arts: dict[str, Any]) -> dict[str, Any]:
    rec = arts.get(key)
    row: dict[str, Any] = {
        "artifact_key": key,
        "primary_label": "missing",
        "reasons": [],
        "review_status": "",
        "generation_id": "",
        "created_at": "",
        "parent_generation_id": "",
    }
    if not isinstance(rec, dict):
        row["reasons"] = ["no_record"]
        return row

    row["review_status"] = str(rec.get("review_status") or "").strip()[:64]
    prov = rec.get("provenance")
    if isinstance(prov, dict):
        row["generation_id"] = str(prov.get("generation_id") or "").strip()[:128]
        row["created_at"] = str(prov.get("created_at") or "").strip()[:64]
        row["parent_generation_id"] = str(prov.get("parent_generation_id") or "").strip()[:128]

    if not _content_nonempty(rec):
        row["reasons"] = ["empty_content"]
        return row

    ok_up, _code, det = assert_upstream_approved(frozenset({key}), arts)
    if not ok_up:
        row["primary_label"] = "blocked"
        row["reasons"] = [det or "upstream_not_approved"]
        return row

    drift = lineage_drift_detail_for_slice(key, arts)
    if drift:
        if is_sealed_conflict(key, arts, drift_reasons=drift):
            row["primary_label"] = "conflicting"
            row["reasons"] = drift + ["sealed_downstream_vs_moved_upstream"]
            return row
        row["primary_label"] = "stale"
        row["reasons"] = drift
        return row

    qf = _quality_failures(rec)
    rs = str(rec.get("review_status") or "").strip().lower()
    if qf:
        row["primary_label"] = "draft"
        row["reasons"] = qf
        return row

    if rs in ("pending", "changes_requested"):
        row["primary_label"] = "draft"
        row["reasons"] = [f"review_status:{rs}"]
        return row

    if record_approved(rec):
        row["primary_label"] = "approved"
        row["reasons"] = []
        return row

    row["primary_label"] = "present"
    row["reasons"] = []
    return row


def _worst_label(labels: list[str]) -> str:
    best = "present"
    best_r = SEVERITY_RANK.get(best, 0)
    for lb in labels:
        r = SEVERITY_RANK.get(lb, 0)
        if r > best_r:
            best_r = r
            best = lb
    return best


def build_recheck_report(arts: dict[str, Any]) -> dict[str, Any]:
    """Full structured report (schema_version 1)."""
    artifacts_out: list[dict[str, Any]] = []
    for key in ARTIFACT_SLICE_KEYS:
        artifacts_out.append(_inspect_row(key, arts))

    buckets_map: dict[str, list[str]] = {"planning": [], "engineering": [], "execution": [], "unknown": []}
    labels_by_bucket: dict[str, list[str]] = defaultdict(list)
    for row in artifacts_out:
        k = row["artifact_key"]
        b = _bucket_for_key(k)
        buckets_map.setdefault(b, []).append(k)
        labels_by_bucket[b].append(str(row["primary_label"]))

    buckets: list[dict[str, Any]] = []
    for bid in ("planning", "engineering", "execution"):
        lbls = labels_by_bucket.get(bid, [])
        buckets.append(
            {
                "id": bid,
                "worst_label": _worst_label(lbls) if lbls else "present",
                "artifact_keys": sorted(buckets_map.get(bid, [])),
            }
        )

    stale_keys = [r["artifact_key"] for r in artifacts_out if r["primary_label"] == "stale"]
    conflicting_keys = [r["artifact_key"] for r in artifacts_out if r["primary_label"] == "conflicting"]
    blocked_rows = [r for r in artifacts_out if r["primary_label"] == "blocked"]

    regen_seed = frozenset(stale_keys + conflicting_keys)
    regenerate_keys = transitive_downstream(regen_seed) if regen_seed else []

    approve_first_set: set[str] = set()
    for row in blocked_rows:
        ak = str(row.get("artifact_key") or "")
        if ak:
            approve_first_set.update(list_blocking_upstream_keys(ak, arts))
    approve_first = sorted(approve_first_set)

    unlock_candidates: list[str] = []
    for row in artifacts_out:
        k = row["artifact_key"]
        rec = arts.get(k)
        if not isinstance(rec, dict):
            continue
        if rec.get("locked") is not True and str(rec.get("review_status") or "").strip().lower() != "locked":
            continue
        drift = lineage_drift_detail_for_slice(k, arts)
        if drift:
            unlock_candidates.append(k)

    flag_notes: list[str] = []
    for k in conflicting_keys:
        flag_notes.append(f"Conflict (sealed downstream vs moved upstream): {k}")

    recommendations: dict[str, Any] = {
        "regenerate_keys": regenerate_keys,
        "approve_first": approve_first,
        "unlock_or_request_changes": sorted(unlock_candidates),
        "flag_for_review": flag_notes[:64],
    }

    return {
        "schema_version": 1,
        "computed_at": _utc_now_iso(),
        "artifacts": artifacts_out,
        "buckets": buckets,
        "recommendations": recommendations,
    }


