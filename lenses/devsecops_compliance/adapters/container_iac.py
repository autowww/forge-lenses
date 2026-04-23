"""Container / IaC scanning → ``security_finding`` (category container|iac)."""

from __future__ import annotations

from typing import Any


def normalize_trivy_vulnerability(raw: dict[str, Any], *, project: str = "", artifact: str = "") -> dict[str, Any]:
    vid = str(raw.get("VulnerabilityID") or raw.get("vulnerability_id") or "")
    sev = str(raw.get("Severity") or raw.get("severity") or "medium").lower()
    return {
        "canonical_kind": "security_finding",
        "finding_id": f"trivy-{vid}-{artifact}".strip("-"),
        "project": project,
        "provider": "trivy",
        "category": "container",
        "severity": sev,
        "state": "open",
        "title": str(raw.get("Title") or vid or "Trivy finding"),
        "rule_id": vid,
        "file_path": artifact,
        "url": "",
        "detected_at": "",
        "cve_id": vid if vid.startswith("CVE-") else "",
    }


def normalize_trivy_misconfig(raw: dict[str, Any], *, project: str = "", file_path: str = "") -> dict[str, Any]:
    mid = str(raw.get("ID") or raw.get("id") or "")
    return {
        "canonical_kind": "security_finding",
        "finding_id": f"trivy-iac-{mid}",
        "project": project,
        "provider": "trivy",
        "category": "iac",
        "severity": str(raw.get("Severity") or "medium").lower(),
        "state": "open",
        "title": str(raw.get("Title") or mid or "IaC misconfiguration"),
        "rule_id": mid,
        "file_path": file_path,
        "url": "",
        "detected_at": "",
    }
