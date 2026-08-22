"""Merge quality gate failures into CI/CD ``blocked_promotions``."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from lenses.test_quality.feature_flag import experimental_test_quality_enabled
from lenses.test_quality.gates import evaluate_quality_gates, quality_gate_promotion_blockers
from lenses.test_quality.story_evidence import load_doc_for_workspace


def extend_blocked_promotions_with_quality_gates(
    blocked: list[dict[str, Any]],
    *,
    workspace_root: Path,
    scan_state: dict[str, Any],
    cicd_doc: dict[str, Any],
) -> list[str]:
    """Mutate ``blocked`` in place; return hint strings for control tower."""
    hints: list[str] = []
    if not experimental_test_quality_enabled():
        return hints

    lenses_root = Path(__file__).resolve().parent.parent
    qdoc = load_doc_for_workspace(workspace_root, lenses_root)
    if qdoc is None:
        return hints

    children = scan_state.get("children")
    if not isinstance(children, list):
        children = []
    child_names = {str(c.get("name") or "").strip() for c in children if isinstance(c, dict)}
    child_names.discard("")

    promotions = [p for p in cicd_doc.get("promotions") or [] if isinstance(p, dict)]

    proj_hint = ""
    if child_names:
        prefer = sorted(child_names & {"forgesdlc"})
        proj_hint = prefer[0] if prefer else sorted(child_names)[0]

    evaluations, _ = evaluate_quality_gates(qdoc, project_filter=proj_hint or None)
    seen_keys = {f"{b.get('promotion_id')}:{b.get('reason')}" for b in blocked}
    extras = quality_gate_promotion_blockers(evaluations, promotions)
    for row in extras:
        key = f"{row.get('promotion_id')}:{row.get('reason')}"
        if key in seen_keys:
            continue
        seen_keys.add(key)
        blocked.append(dict(row))

    if any(not e.get("passed") for e in evaluations):
        hints.append("One or more quality gates failed — promotions may be blocked (see blocked_promotions).")

    return hints
