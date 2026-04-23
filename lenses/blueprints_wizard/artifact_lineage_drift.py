"""Shared lineage drift detection for artifact generation recheck (no I/O)."""

from __future__ import annotations

from typing import Any

from lenses.blueprints_wizard.artifact_generation_dependencies import _approved as upstream_approved_record
from lenses.blueprints_wizard.artifact_generation_normalize import ARTIFACT_SLICE_KEYS


def lineage_drift_detail_for_slice(artifact_key: str, arts: dict[str, Any]) -> list[str]:
    """
    Return human-readable drift reasons for ``artifact_key`` (empty if no drift).
    Mirrors drift rules in ``summarize_artifact_generation_recheck`` for one slice.
    """
    reasons: list[str] = []
    rec = arts.get(artifact_key)
    if not isinstance(rec, dict):
        return reasons
    prov = rec.get("provenance")
    if not isinstance(prov, dict):
        return reasons
    lin = prov.get("lineage")
    if not isinstance(lin, dict):
        return reasons
    ups = lin.get("upstream")
    if not isinstance(ups, list):
        return reasons
    for u in ups:
        if not isinstance(u, dict):
            continue
        uak = str(u.get("artifact_key") or "").strip()
        ugid = str(u.get("generation_id") or "").strip()
        if not uak or not ugid:
            continue
        cur = arts.get(uak)
        if not isinstance(cur, dict):
            reasons.append(f"lineage_drift:{artifact_key}:missing_upstream:{uak}")
            continue
        cup = cur.get("provenance")
        if not isinstance(cup, dict):
            reasons.append(f"lineage_drift:{artifact_key}:no_prov:{uak}")
            continue
        cur_id = str(cup.get("generation_id") or "").strip()
        if cur_id and cur_id != ugid:
            reasons.append(f"lineage_drift:{artifact_key}:{uak}")
    return reasons


def _downstream_sealed(rec: Any) -> bool:
    if not isinstance(rec, dict):
        return False
    rs = str(rec.get("review_status") or "").strip().lower()
    if rs in ("approved", "locked"):
        return True
    return rec.get("locked") is True


def is_sealed_conflict(
    artifact_key: str,
    arts: dict[str, Any],
    *,
    drift_reasons: list[str],
) -> bool:
    """
    True when this slice is approved/locked, has lineage drift vs an upstream,
    and that upstream record is currently approved — sealed downstream vs moved upstream.
    """
    if not drift_reasons:
        return False
    rec = arts.get(artifact_key)
    if not _downstream_sealed(rec):
        return False
    prov = rec.get("provenance")
    if not isinstance(prov, dict):
        return False
    lin = prov.get("lineage")
    if not isinstance(lin, dict):
        return False
    ups = lin.get("upstream")
    if not isinstance(ups, list):
        return False
    for u in ups:
        if not isinstance(u, dict):
            continue
        uak = str(u.get("artifact_key") or "").strip()
        ugid = str(u.get("generation_id") or "").strip()
        if not uak or not ugid:
            continue
        cur = arts.get(uak)
        if not isinstance(cur, dict):
            continue
        cup = cur.get("provenance")
        if not isinstance(cup, dict):
            continue
        cur_id = str(cup.get("generation_id") or "").strip()
        if not cur_id or cur_id == ugid:
            continue
        if upstream_approved_record(cur):
            return True
    return False


def collect_all_lineage_drift_issue_strings(arts: dict[str, Any]) -> list[str]:
    """Flatten drift strings for all slices (for ``recheck_summary.issues`` compatibility)."""
    issues: list[str] = []
    for key in ARTIFACT_SLICE_KEYS:
        for r in lineage_drift_detail_for_slice(key, arts):
            issues.append(r)
    return issues
