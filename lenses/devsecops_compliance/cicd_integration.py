"""Merge security policy failures into control tower ``blocked_promotions`` and gate hints."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from lenses.devsecops_compliance.aggregate import _load_doc, _now_iso, _security_release_gate
from lenses.devsecops_compliance.feature_flag import experimental_devsecops_compliance_enabled
from lenses.devsecops_compliance.ingest import expand_ingestions
from lenses.devsecops_compliance.policy_engine import evaluate_security_policy_checks, security_policy_promotion_blockers
from lenses.devsecops_compliance.risk_engine import compute_risk_score


def merge_devsecops_into_control_tower_payload(
    payload: dict[str, Any],
    *,
    workspace_root: Path,
    scan_state: dict[str, Any],
) -> None:
    """Mutate ``payload`` (blocked_promotions, hints, security_release_gate)."""
    if not experimental_devsecops_compliance_enabled():
        return

    raw = _load_doc(workspace_root)
    if raw is None:
        return

    doc = expand_ingestions(raw)
    now = _now_iso()
    risk = compute_risk_score(doc, now_iso=now)
    evaluations = evaluate_security_policy_checks(doc, now_iso=now)
    gate = _security_release_gate(evaluations, risk)
    payload["security_release_gate"] = gate

    promotions = [p for p in payload.get("promotions") or [] if isinstance(p, dict)]
    blocked = payload.get("blocked_promotions")
    if not isinstance(blocked, list):
        blocked = []
        payload["blocked_promotions"] = blocked

    seen = {f"{b.get('promotion_id')}:{b.get('reason')}" for b in blocked}
    for row in security_policy_promotion_blockers(evaluations, promotions):
        key = f"{row.get('promotion_id')}:{row.get('reason')}"
        if key in seen:
            continue
        seen.add(key)
        blocked.append(dict(row))

    hints = payload.get("hints")
    if not isinstance(hints, list):
        hints = []
        payload["hints"] = hints
    if any(not e.get("passed") for e in evaluations):
        hints.append("Security or compliance policy failed — see security_release_gate and blocked_promotions.")
