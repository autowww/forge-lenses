"""Recheck stub: prerequisites + quality thresholds for ``artifact_generation`` (no I/O)."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from lenses.blueprints_wizard.artifact_generation_normalize import ARTIFACT_SLICE_KEYS, QUALITY_DIMENSIONS
from lenses.blueprints_wizard.artifact_generation_inputs import validate_generation_prerequisites
from lenses.blueprints_wizard.artifact_lineage_drift import collect_all_lineage_drift_issue_strings
from lenses.blueprints_wizard.recheck_status_engine import build_recheck_report
from lenses.blueprints_wizard.schemas import CURRENT_VERSION, WizardSessionDocument
from lenses.blueprints_wizard.wizard_domain_normalize import (
    normalize_artifact_generation,
    normalize_recheck_summary,
    normalize_recheck_report,
)

# Minimum score (0..1) per dimension for a slice to count as "passing" quality bar.
MIN_QUALITY_SCORE = 0.5


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _doc_from_payload(payload: dict[str, Any]) -> WizardSessionDocument | None:
    if not isinstance(payload, dict):
        return None
    return WizardSessionDocument.from_dict(
        {
            "version": CURRENT_VERSION,
            "updated_at": _utc_now_iso(),
            "step_index": 0,
            "payload": payload,
        }
    )


def summarize_artifact_generation_recheck(payload: dict[str, Any]) -> dict[str, Any]:
    """
    Evaluate session **payload**: generation prerequisites, per-slice quality for **present**
    artifacts only, provenance lineage drift vs current upstream generation ids, and structured
    ``report`` (schema v1).
    """
    issues: list[str] = []
    doc = _doc_from_payload(payload)
    wd: dict[str, Any] = {}
    if isinstance(payload.get("wizard_domain"), dict):
        wd = payload["wizard_domain"]  # type: ignore[assignment]
    ag = normalize_artifact_generation(wd.get("artifact_generation"))
    arts = ag.get("artifacts") or {}
    if not isinstance(arts, dict):
        arts = {}

    if doc is None:
        rep = normalize_recheck_report(build_recheck_report({}))
        return normalize_recheck_summary(
            {
                "checked_at": _utc_now_iso(),
                "passed": False,
                "issues": ["invalid_payload"],
                "report": rep,
            }
        )

    ok_pre, err = validate_generation_prerequisites(doc)
    if not ok_pre:
        issues.append(f"prerequisites:{err or 'not_met'}")

    for key in ARTIFACT_SLICE_KEYS:
        rec = arts.get(key)
        if not isinstance(rec, dict):
            continue
        q = rec.get("quality")
        if not isinstance(q, dict):
            issues.append(f"quality_missing:{key}")
            continue
        for dim in QUALITY_DIMENSIONS:
            entry = q.get(dim)
            if not isinstance(entry, dict):
                issues.append(f"quality:{key}:{dim}:missing")
                continue
            try:
                score = float(entry.get("score", 0))
            except (TypeError, ValueError):
                score = 0.0
            if score < MIN_QUALITY_SCORE:
                issues.append(f"quality:{key}:{dim}:below_threshold")

    issues.extend(collect_all_lineage_drift_issue_strings(arts))

    passed = len(issues) == 0
    report_raw = build_recheck_report(arts)
    report_norm = normalize_recheck_report(report_raw)
    return normalize_recheck_summary(
        {
            "checked_at": _utc_now_iso(),
            "passed": passed,
            "issues": issues[:128],
            "report": report_norm,
        }
    )


class ArtifactGenerationRecheckStub:
    """``RecheckProvider`` implementation: artifact generation prerequisites + quality bar + report."""

    def summarize(self, payload: dict[str, Any]) -> dict[str, Any]:
        return summarize_artifact_generation_recheck(payload)
