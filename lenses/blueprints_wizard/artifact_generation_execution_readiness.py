"""Scope readiness for execution artifact generation (experimental Blueprints Wizard)."""

from __future__ import annotations

import json
from typing import Any

from lenses.blueprints_wizard.schemas import WizardSessionDocument
from lenses.blueprints_wizard.wizard_domain_normalize import normalize_scope_spec


def scope_fingerprint_payload(payload: dict[str, Any]) -> dict[str, Any]:
    """Canonical JSON-serializable scope for provenance fingerprinting."""
    wd = payload.get("wizard_domain")
    spec: dict[str, Any] = {}
    if isinstance(wd, dict):
        spec = normalize_scope_spec(wd.get("scope_spec"))
    scope = payload.get("scope")
    wbs_rel = ""
    roadmap_rel = ""
    if isinstance(scope, dict):
        wbs_rel = str(scope.get("wbs_rel") or "").strip()
        roadmap_rel = str(scope.get("roadmap_rel") or "").strip()
    return {
        "scope_spec": spec,
        "payload_scope": {"wbs_rel": wbs_rel, "roadmap_rel": roadmap_rel},
    }


def scope_prompt_block(payload: dict[str, Any]) -> str:
    """Human-readable scope context for LLM prompts (deterministic)."""
    blob = scope_fingerprint_payload(payload)
    try:
        text = json.dumps(blob, sort_keys=True, ensure_ascii=False, indent=2)
    except (TypeError, ValueError):
        text = str(blob)
    return "--- Scope context (must respect; execution work stays inside this boundary) ---\n\n" + text + "\n"


def validate_scope_complete_for_execution(doc: WizardSessionDocument) -> tuple[bool, str | None, str | None]:
    """
    Returns (ok, error_code, detail) when ``scope_spec`` contradicts selected ``scope_boundary``.
    """
    pl = doc.payload
    if not isinstance(pl, dict):
        return False, "invalid_payload", ""
    wd = pl.get("wizard_domain")
    if not isinstance(wd, dict):
        return True, None, None
    spec = normalize_scope_spec(wd.get("scope_spec"))
    boundary = str(spec.get("scope_boundary") or "full_plan").strip().lower()

    def _non_empty(s: Any) -> bool:
        return bool(str(s or "").strip())

    if boundary == "milestone" and not _non_empty(spec.get("milestone_ref")):
        return False, "scope_incomplete", "milestone_ref required when scope_boundary is milestone"

    if boundary == "wbe_subtree" and not _non_empty(spec.get("wbe_path")):
        return False, "scope_incomplete", "wbe_path required when scope_boundary is wbe_subtree"

    if boundary == "capability" and not _non_empty(spec.get("capability_label")):
        return False, "scope_incomplete", "capability_label required when scope_boundary is capability"

    if boundary == "team_slice" and not _non_empty(spec.get("team_label")):
        return False, "scope_incomplete", "team_label required when scope_boundary is team_slice"

    if boundary == "repo_path":
        rp = spec.get("repo_paths")
        if not isinstance(rp, list) or not any(isinstance(x, str) and x.strip() for x in rp):
            return False, "scope_incomplete", "repo_paths required when scope_boundary is repo_path"

    if boundary == "recheck_subset" and not _non_empty(spec.get("recheck_issue_refs")):
        return False, "scope_incomplete", "recheck_issue_refs required when scope_boundary is recheck_subset"

    return True, None, None
