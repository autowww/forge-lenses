"""Inputs and prerequisites for artifact generation (mirror Studio rules)."""

from __future__ import annotations

from typing import Any

from lenses.blueprints_wizard.schemas import WizardSessionDocument
from lenses.blueprints_wizard.wizard_domain_normalize import normalize_foundation_brief, normalize_run_plan

# Aligned with runPlanStep.ts RUN_PLAN_MAX_STEPS / payload_validate.
_RUN_PLAN_MAX_STEPS = 32


def effective_foundation_brief_markdown(payload: dict[str, Any]) -> str:
    """Prefer `wizard_domain.foundation_brief.markdown`, else legacy string `payload.foundation_brief`."""
    wd = payload.get("wizard_domain")
    if isinstance(wd, dict):
        fb = normalize_foundation_brief(wd.get("foundation_brief"))
        dm = str(fb.get("markdown", "")).strip()
        if dm:
            return str(fb.get("markdown", ""))
    leg = payload.get("foundation_brief")
    if isinstance(leg, str) and leg.strip():
        return leg
    return ""


def run_plan_valid_for_generation(doc: WizardSessionDocument) -> tuple[bool, str]:
    """Mirror `validateRunPlanForNext` from runPlanStep.ts."""
    wd = doc.payload.get("wizard_domain")
    if not isinstance(wd, dict):
        return False, "invalid_run_plan"
    rp = normalize_run_plan(wd.get("run_plan"))
    title = str(rp.get("title", "")).strip()
    if not title:
        return False, "run_plan_needs_title"
    steps = rp.get("steps")
    if not isinstance(steps, list) or len(steps) == 0:
        return False, "run_plan_needs_steps"
    if len(steps) > _RUN_PLAN_MAX_STEPS:
        return False, "run_plan_too_many_steps"
    for i, s in enumerate(steps):
        if not isinstance(s, dict):
            return False, "invalid_run_plan_step"
        if not str(s.get("title", "")).strip():
            return False, "run_plan_step_needs_title"
    return True, ""


def validate_generation_prerequisites(doc: WizardSessionDocument) -> tuple[bool, str]:
    """Non-empty foundation brief + valid run plan."""
    pl = doc.payload
    if not isinstance(pl, dict):
        return False, "invalid_payload"
    brief = effective_foundation_brief_markdown(pl).strip()
    if not brief:
        return False, "prerequisites_not_met"
    ok, err = run_plan_valid_for_generation(doc)
    if not ok:
        return False, err or "prerequisites_not_met"
    return True, ""


def canonical_inputs_fingerprint_payload(
    payload: dict[str, Any],
    *,
    upstream_generation_ids: dict[str, str] | None = None,
    include_execution_scope: bool = False,
) -> str:
    """Stable hash input for provenance (brief, run plan, optional upstream generation ids)."""
    import hashlib
    import json

    from lenses.blueprints_wizard.artifact_generation_execution_readiness import scope_fingerprint_payload

    brief = effective_foundation_brief_markdown(payload)
    wd = payload.get("wizard_domain")
    rp: dict[str, Any] = {}
    if isinstance(wd, dict):
        rp = normalize_run_plan(wd.get("run_plan"))
    ug: dict[str, str] = {}
    if upstream_generation_ids:
        for k, v in upstream_generation_ids.items():
            ks = str(k).strip()
            vs = str(v).strip()
            if ks and vs:
                ug[ks] = vs[:128]
    blob: dict[str, Any] = {"foundation_brief": brief, "run_plan": rp}
    if ug:
        blob["upstream_generations"] = ug
    if include_execution_scope:
        blob["execution_scope"] = scope_fingerprint_payload(payload)
    canonical = json.dumps(blob, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def upstream_generation_id_map(arts: dict[str, Any], upstream_keys: frozenset[str]) -> dict[str, str]:
    """Map artifact_key -> generation_id for approved upstream rows (fingerprint component)."""
    out: dict[str, str] = {}
    for k in upstream_keys:
        rec = arts.get(k)
        if not isinstance(rec, dict):
            continue
        prov = rec.get("provenance")
        if not isinstance(prov, dict):
            continue
        gid = str(prov.get("generation_id") or "").strip()
        if gid:
            out[k] = gid
    return out
