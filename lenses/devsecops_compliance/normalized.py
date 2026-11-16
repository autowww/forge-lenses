"""Canonical DevSecOps / compliance models (Sprint 6) — JSON dicts for APIs."""

from __future__ import annotations

from typing import Any

SCHEMA_VERSION = 1


def empty_devsecops_overview() -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "security_findings": [],
        "vulnerabilities": [],
        "secret_exposures": [],
        "dependency_risks": [],
        "sbom_components": [],
        "provenance_attestations": [],
        "controls": [],
        "exceptions": [],
        "policy_decisions": [],
        "rollups": {},
        "policy_check_evaluations": [],
        "risk_score": None,
        "security_release_gate": None,
    }
