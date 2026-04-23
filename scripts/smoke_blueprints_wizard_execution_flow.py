#!/usr/bin/env python3
"""
Smoke walkthrough for execution artifacts (mock LLM), mirroring manual Review & Generate.

Run from forge-lenses repo root:
  LENSES_ARTIFACT_GENERATION_MOCK=1 python3 scripts/smoke_blueprints_wizard_execution_flow.py

Uses the same Python entrypoints as HTTP handlers (no browser).
"""
from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

# Must set before importing lenses.blueprints_wizard.*
os.environ.setdefault("LENSES_ARTIFACT_GENERATION_MOCK", "1")

from lenses.blueprints_wizard.api import post_artifact_export, post_artifact_recheck
from lenses.blueprints_wizard.artifact_generation_service import apply_artifact_review, generate_artifacts
from lenses.blueprints_wizard.schemas import WizardSessionDocument, normalize_wizard_payload
from lenses.blueprints_wizard.session_store import create_session, load_session, save_session_replace
from lenses.blueprints_wizard.wizard_domain_normalize import (
    normalize_run_plan,
    normalize_scope_spec,
    normalize_wizard_domain,
)


def _session_with_brief_and_plan(root: Path) -> str:
    sid = create_session(root)
    doc = load_session(root, sid)
    assert doc is not None
    pl = dict(doc.payload)
    wd = dict(pl.get("wizard_domain") or {})
    wd["foundation_brief"] = {"markdown": "# Brief\n\nSmoke test.", "field_statuses": {}}
    wd["run_plan"] = normalize_run_plan(
        {"title": "Smoke plan", "steps": [{"id": "s1", "title": "Step", "detail": "d"}]}
    )
    wd["scope_spec"] = normalize_scope_spec({"scope_boundary": "full_plan"})
    pl["wizard_domain"] = normalize_wizard_domain(wd)
    pl["foundation_brief"] = "# Brief\n\nSmoke test."
    doc2 = WizardSessionDocument.from_dict({**doc.to_dict(), "payload": normalize_wizard_payload(pl)})
    assert doc2 is not None
    save_session_replace(root, sid, doc2.to_dict())
    return sid


def main() -> int:
    root = Path(tempfile.mkdtemp(prefix="lenses-bpw-smoke-"))
    print(f"Workspace: {root}")

    # 1) Planning + engineering (mock), approve key upstreams for execution
    sid = _session_with_brief_and_plan(root)
    r1 = generate_artifacts(root, sid, {"provider": "openai", "artifact_bundle": "all"})
    assert r1.get("ok") is True, r1
    print("OK: generate planning+engineering (artifact_bundle=all)")

    # Approve slices required before execution batch (wbe_tree, prd) when not generated together
    for k in ("foundation_brief_final", "roadmap", "milestone_outline", "milestone_charters"):
        apply_artifact_review(root, sid, {"action": "approve", "artifact_key": k})
    for k in ("wbe_tree", "prd", "dependency_map", "architecture_brief", "nfr_checklist", "adr_seeds", "ownership_review_matrix"):
        apply_artifact_review(root, sid, {"action": "approve", "artifact_key": k})
    print("OK: approved planning + engineering slices")

    r2 = generate_artifacts(root, sid, {"provider": "openai", "artifact_bundle": "execution"})
    assert r2.get("ok") is True, r2
    print("OK: generate execution pack")

    # 2) scope_incomplete: milestone without milestone_ref
    sid_bad = _session_with_brief_and_plan(root)
    doc = load_session(root, sid_bad)
    assert doc is not None
    pl = dict(doc.payload)
    wd = dict(pl.get("wizard_domain") or {})
    wd["scope_spec"] = normalize_scope_spec({"scope_boundary": "milestone", "milestone_ref": ""})
    pl["wizard_domain"] = normalize_wizard_domain(wd)
    doc2 = WizardSessionDocument.from_dict({**doc.to_dict(), "payload": normalize_wizard_payload(pl)})
    assert doc2 is not None
    save_session_replace(root, sid_bad, doc2.to_dict())
    r3 = generate_artifacts(root, sid_bad, {"provider": "openai", "artifact_bundle": "execution"})
    assert r3.get("ok") is False and r3.get("error") == "scope_incomplete", r3
    print("OK: execution blocked with scope_incomplete (milestone, empty milestone_ref)")

    # 3) Approve bundle + export + recheck on good session
    ex_keys = ["sparks_plan", "implementation_tasklets", "rollout_notes"]
    r4 = apply_artifact_review(
        root,
        sid,
        {"action": "approve_bundle", "artifact_keys": ex_keys},
    )
    assert r4.get("ok") is True, r4
    print("OK: approve_bundle selected execution keys")

    r5 = post_artifact_export(root, sid, {"artifact_keys": ex_keys})
    assert r5.get("ok") is True and "markdown" in r5 and len(r5["markdown"]) > 50, r5
    print("OK: artifact-export markdown length:", len(r5["markdown"]))

    r6a = post_artifact_recheck(root, sid, {"dry_run": True})
    assert r6a.get("ok") is True and r6a.get("dry_run") is True, r6a
    assert "session" not in r6a
    print("OK: artifact-recheck dry_run (no save)")

    r6 = post_artifact_recheck(root, sid, {})
    assert r6.get("ok") is True, r6
    print("OK: artifact-recheck", "passed" if r6.get("recheck_summary", {}).get("passed") else "issues")

    print("\nAll smoke steps passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
