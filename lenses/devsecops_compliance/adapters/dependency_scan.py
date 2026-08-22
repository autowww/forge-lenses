"""Dependency scanning → ``vulnerability`` + optional ``dependency_risk``."""

from __future__ import annotations

from typing import Any


def normalize_dependabot_alert(raw: dict[str, Any], *, project: str = "") -> dict[str, Any]:
    sec = raw.get("security_advisory") if isinstance(raw.get("security_advisory"), dict) else {}
    cve = str(sec.get("cve_id") or raw.get("cve_id") or "")
    ghsa = str(sec.get("ghsa_id") or raw.get("ghsa_id") or "")
    sev = str(sec.get("severity") or raw.get("severity") or "medium").lower()
    return {
        "canonical_kind": "vulnerability",
        "vuln_id": str(raw.get("number") or raw.get("id") or ""),
        "project": project,
        "provider": "dependabot",
        "severity": sev,
        "state": str(raw.get("state") or "open").lower(),
        "title": str(sec.get("summary") or raw.get("title") or "Dependency advisory"),
        "cve_id": cve,
        "ghsa_id": ghsa,
        "package_ecosystem": str((raw.get("dependency") or {}).get("package", {}).get("ecosystem") or ""),
        "package_name": str((raw.get("dependency") or {}).get("package", {}).get("name") or ""),
        "url": str(raw.get("html_url") or ""),
        "detected_at": str(raw.get("created_at") or ""),
    }


def normalize_snyk_issue(raw: dict[str, Any], *, project: str = "") -> tuple[dict[str, Any], dict[str, Any]]:
    sev = str(raw.get("severity") or "medium").lower()
    vid = str(raw.get("id") or "")
    vuln = {
        "canonical_kind": "vulnerability",
        "vuln_id": vid,
        "project": project,
        "provider": "snyk",
        "severity": sev,
        "state": str(raw.get("status") or "open").lower(),
        "title": str(raw.get("title") or "Snyk issue"),
        "cve_id": str(raw.get("identifiers", {}).get("CVE", [""])[0] if isinstance(raw.get("identifiers"), dict) else ""),
        "ghsa_id": "",
        "package_ecosystem": "",
        "package_name": str(raw.get("packageName") or ""),
        "url": str(raw.get("url") or ""),
        "detected_at": "",
    }
    risk = {
        "canonical_kind": "dependency_risk",
        "risk_id": f"dep-{vid}",
        "project": project,
        "package_name": vuln["package_name"],
        "severity": sev,
        "direct": bool(raw.get("isUpgradable")),
        "url": vuln["url"],
    }
    return vuln, risk
