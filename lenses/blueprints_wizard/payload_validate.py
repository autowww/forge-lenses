"""Validate wizard payload paths and references (scope, parent session)."""

from __future__ import annotations

from pathlib import Path

from lenses.blueprints_wizard.schemas import WizardSessionDocument
from lenses.blueprints_wizard.scope_paths import safe_roadmap_file, safe_wbs_file
from lenses.blueprints_wizard.session_store import load_session, validate_session_id

# Aligned with `runPlanStep.ts` RUN_PLAN_MAX_STEPS.
_RUN_PLAN_MAX_STEPS = 32


def validate_wizard_run_plan(doc: WizardSessionDocument) -> tuple[bool, str]:
    """Reject pathological run_plan lists after normalization (PUT session)."""
    pl = doc.payload
    wd = pl.get("wizard_domain")
    if not isinstance(wd, dict):
        return True, ""
    rp = wd.get("run_plan")
    if not isinstance(rp, dict):
        return False, "invalid_run_plan"
    steps = rp.get("steps")
    if not isinstance(steps, list):
        return False, "invalid_run_plan_steps"
    if len(steps) > _RUN_PLAN_MAX_STEPS:
        return False, "run_plan_too_many_steps"
    for s in steps:
        if s is not None and not isinstance(s, dict):
            return False, "invalid_run_plan_step"
    return True, ""


def validate_wizard_payload_paths(workspace_root: Path, doc: WizardSessionDocument) -> tuple[bool, str]:
    pl = doc.payload
    scope = pl.get("scope")
    if scope is None:
        return True, ""
    if not isinstance(scope, dict):
        return False, "invalid_scope"
    wbs = scope.get("wbs_rel")
    if wbs:
        if not isinstance(wbs, str) or safe_wbs_file(workspace_root, wbs) is None:
            return False, "invalid_wbs_rel"
    rm = scope.get("roadmap_rel")
    if rm:
        if not isinstance(rm, str) or safe_roadmap_file(workspace_root, rm) is None:
            return False, "invalid_roadmap_rel"
    parent = pl.get("parent_session_id")
    if parent:
        if not isinstance(parent, str) or not validate_session_id(parent):
            return False, "invalid_parent_session_id"
        if load_session(workspace_root, parent) is None:
            return False, "parent_session_not_found"
    ok_rp, err_rp = validate_wizard_run_plan(doc)
    if not ok_rp:
        return False, err_rp
    return True, ""
