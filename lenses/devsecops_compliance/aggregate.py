"""Build ``GET /api/devsecops/overview`` and per-project payloads."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from lenses.devsecops_compliance.feature_flag import experimental_devsecops_compliance_enabled
from lenses.devsecops_compliance.ingest import expand_ingestions
from lenses.devsecops_compliance.local_store import load_demo_fixture, read_local_devsecops_compliance
from lenses.devsecops_compliance.normalized import SCHEMA_VERSION, empty_devsecops_overview
from lenses.devsecops_compliance.policy_engine import evaluate_security_policy_checks
from lenses.devsecops_compliance.risk_engine import compute_risk_score
from lenses.devsecops_compliance.rollups import build_rollups


def _lenses_root() -> Path:
    return Path(__file__).resolve().parent.parent


def _truthy_env(name: str) -> bool:
    raw = (os.environ.get(name) or "").strip().lower()
    return raw in ("1", "true", "yes", "on")


def _load_doc(workspace_root: Path) -> dict[str, Any] | None:
    doc = read_local_devsecops_compliance(workspace_root)
    if doc is not None:
        return doc
    if _truthy_env("LENSES_DEVSECOPS_COMPLIANCE_SEED_DEMO"):
        return load_demo_fixture(_lenses_root())
    return None


def _now_iso() -> str:
    from datetime import datetime, timezone

    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _security_release_gate(
    policy_evals: list[dict[str, Any]],
    risk: dict[str, Any],
) -> dict[str, Any]:
    failed = [e for e in policy_evals if not e.get("passed")]
    return {
        "passed": len(failed) == 0,
        "failed_policy_ids": [str(e.get("policy_id")) for e in failed],
        "risk_score": risk,
        "summary": "All security/compliance policies passed"
        if not failed
        else f"{len(failed)} policy check(s) failed; risk score {risk.get('value')}",
    }


def build_devsecops_overview_payload(
    *,
    workspace_root: Path,
    scan_state: dict[str, Any],
    force_flag: bool | None = None,
) -> dict[str, Any]:
    enabled = experimental_devsecops_compliance_enabled() if force_flag is None else bool(force_flag)
    children = scan_state.get("children")
    if not isinstance(children, list):
        children = []
    git_count = sum(1 for c in children if isinstance(c, dict) and c.get("is_git"))

    if not enabled:
        base = empty_devsecops_overview()
        return {
            "ok": True,
            **base,
            "feature_enabled": False,
            "provider_kind": "disabled",
            "resolved_at": scan_state.get("resolved_at"),
            "workspace_summary": {"child_count": len(children), "git_repo_count": git_count},
            "hints": [
                "DevSecOps / compliance orchestration is off (LENSES_EXPERIMENTAL_DEVSECOPS_COMPLIANCE=0).",
                "When on, use `.lenses-local/devsecops-compliance.json` or LENSES_DEVSECOPS_COMPLIANCE_SEED_DEMO=1.",
            ],
        }

    raw_doc = _load_doc(workspace_root)
    if raw_doc is None:
        base = empty_devsecops_overview()
        return {
            "ok": True,
            **base,
            "feature_enabled": True,
            "provider_kind": "scan_only",
            "resolved_at": scan_state.get("resolved_at"),
            "workspace_summary": {"child_count": len(children), "git_repo_count": git_count},
            "hints": [
                "No `.lenses-local/devsecops-compliance.json` — add one or set "
                "LENSES_DEVSECOPS_COMPLIANCE_SEED_DEMO=1 for findings, SBOM, provenance, controls, exceptions, policies.",
            ],
        }

    doc = expand_ingestions(raw_doc)
    now = _now_iso()
    risk = compute_risk_score(doc, now_iso=now)
    rollups = build_rollups(doc)
    policy_evals = evaluate_security_policy_checks(doc, now_iso=now)
    gate = _security_release_gate(policy_evals, risk)

    return {
        "ok": True,
        "schema_version": SCHEMA_VERSION,
        "feature_enabled": True,
        "provider_kind": "local_fixture",
        "resolved_at": scan_state.get("resolved_at"),
        "workspace_summary": {"child_count": len(children), "git_repo_count": git_count},
        "security_findings": [f for f in doc.get("security_findings") or [] if isinstance(f, dict)][:200],
        "vulnerabilities": [v for v in doc.get("vulnerabilities") or [] if isinstance(v, dict)][:200],
        "secret_exposures": [s for s in doc.get("secret_exposures") or [] if isinstance(s, dict)][:120],
        "dependency_risks": [r for r in doc.get("dependency_risks") or [] if isinstance(r, dict)][:120],
        "sbom_components": [b for b in doc.get("sbom_components") or [] if isinstance(b, dict)][:500],
        "provenance_attestations": [p for p in doc.get("provenance_attestations") or [] if isinstance(p, dict)][:80],
        "controls": [c for c in doc.get("controls") or [] if isinstance(c, dict)],
        "exceptions": [e for e in doc.get("exceptions") or [] if isinstance(e, dict)],
        "policy_decisions": [d for d in doc.get("policy_decisions") or [] if isinstance(d, dict)][:80],
        "policy_check_evaluations": policy_evals,
        "rollups": rollups,
        "risk_score": risk,
        "security_release_gate": gate,
        "hints": [],
    }


def _filter_project(doc: dict[str, Any], project: str) -> dict[str, Any]:
    pn = (project or "").strip()
    out = dict(doc)

    def keep(row: dict[str, Any]) -> bool:
        return str(row.get("project") or "").strip() == pn

    out["security_findings"] = [f for f in doc.get("security_findings") or [] if isinstance(f, dict) and keep(f)]
    out["vulnerabilities"] = [v for v in doc.get("vulnerabilities") or [] if isinstance(v, dict) and keep(v)]
    out["secret_exposures"] = [s for s in doc.get("secret_exposures") or [] if isinstance(s, dict) and keep(s)]
    out["dependency_risks"] = [r for r in doc.get("dependency_risks") or [] if isinstance(r, dict) and keep(r)]
    out["sbom_components"] = [b for b in doc.get("sbom_components") or [] if isinstance(b, dict) and keep(b)]
    out["provenance_attestations"] = [
        p for p in doc.get("provenance_attestations") or [] if isinstance(p, dict) and keep(p)
    ]
    out["controls"] = list(doc.get("controls") or [])
    out["exceptions"] = list(doc.get("exceptions") or [])
    out["security_policies"] = list(doc.get("security_policies") or [])
    out["policy_context"] = dict(doc.get("policy_context") or {})
    out["policy_context"]["project"] = pn
    out["environment_posture"] = [
        e for e in doc.get("environment_posture") or [] if isinstance(e, dict)
    ]
    out["ingestions"] = [
        i for i in doc.get("ingestions") or [] if isinstance(i, dict) and keep(i)
    ]
    return out


def build_project_devsecops_payload(
    *,
    workspace_root: Path,
    scan_state: dict[str, Any],
    project_name: str,
    force_flag: bool | None = None,
) -> dict[str, Any]:
    overview = build_devsecops_overview_payload(
        workspace_root=workspace_root,
        scan_state=scan_state,
        force_flag=force_flag,
    )
    pn = (project_name or "").strip()
    if not overview.get("feature_enabled"):
        return {**overview, "project": pn, "security_summary": None}

    if overview.get("provider_kind") != "local_fixture":
        return {
            "ok": True,
            "schema_version": SCHEMA_VERSION,
            "feature_enabled": True,
            "provider_kind": overview.get("provider_kind"),
            "resolved_at": overview.get("resolved_at"),
            "project": pn,
            "security_summary": None,
            "hints": overview.get("hints") or [],
        }

    raw_doc = _load_doc(workspace_root)
    assert raw_doc is not None
    doc = expand_ingestions(_filter_project(raw_doc, pn))
    now = _now_iso()
    risk = compute_risk_score(doc, now_iso=now)
    rollups = build_rollups(doc)
    policy_evals = evaluate_security_policy_checks(doc, now_iso=now)
    gate = _security_release_gate(policy_evals, risk)

    return {
        "ok": True,
        "schema_version": SCHEMA_VERSION,
        "feature_enabled": True,
        "provider_kind": "local_fixture",
        "resolved_at": overview.get("resolved_at"),
        "project": pn,
        "security_summary": {
            "risk_score": risk,
            "security_release_gate": gate,
            "rollup_repo": (rollups.get("by_repo") or {}).get(pn) or (rollups.get("by_repo") or {}).get("_unscoped"),
        },
        "policy_check_evaluations": policy_evals,
        "security_findings": doc.get("security_findings") or [],
        "vulnerabilities": doc.get("vulnerabilities") or [],
        "secret_exposures": doc.get("secret_exposures") or [],
        "exceptions": doc.get("exceptions") or [],
        "controls": doc.get("controls") or [],
        "sbom_components": doc.get("sbom_components") or [],
        "provenance_attestations": doc.get("provenance_attestations") or [],
        "rollups": rollups,
        "hints": [],
    }
