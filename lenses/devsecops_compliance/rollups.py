"""Security posture rollups by repo, initiative, release, environment."""

from __future__ import annotations

from typing import Any

from lenses.devsecops_compliance.risk_engine import _SEV_W


def _open_severity_counts(rows: list[dict[str, Any]]) -> dict[str, int]:
    c = {"critical": 0, "high": 0, "medium": 0, "low": 0, "open": 0}
    for r in rows:
        if not isinstance(r, dict):
            continue
        if str(r.get("state") or "open").lower() in ("resolved", "fixed", "dismissed", "rotated"):
            continue
        c["open"] += 1
        sev = str(r.get("severity") or "medium").lower()
        if sev in c:
            c[sev] += 1
    return c


def _proj_key(row: dict[str, Any]) -> str:
    return str(row.get("project") or "").strip() or "_unscoped"


def build_rollups(doc: dict[str, Any]) -> dict[str, Any]:
    findings = [f for f in doc.get("security_findings") or [] if isinstance(f, dict)]
    vulns = [v for v in doc.get("vulnerabilities") or [] if isinstance(v, dict)]
    secrets = [s for s in doc.get("secret_exposures") or [] if isinstance(s, dict)]
    risks = [r for r in doc.get("dependency_risks") or [] if isinstance(r, dict)]

    projects: set[str] = set()
    for row in findings + vulns + secrets + risks:
        projects.add(_proj_key(row))

    by_repo: dict[str, dict[str, Any]] = {}
    for p in projects:
        pf = [f for f in findings if _proj_key(f) == p]
        pv = [v for v in vulns if _proj_key(v) == p]
        ps = [s for s in secrets if _proj_key(s) == p]
        pr = [r for r in risks if _proj_key(r) == p]
        w = 0
        for f in pf:
            if str(f.get("state") or "open").lower() in ("resolved", "fixed", "dismissed"):
                continue
            w += _SEV_W.get(str(f.get("severity") or "medium").lower(), 5)
        for v in pv:
            if str(v.get("state") or "open").lower() in ("resolved", "fixed", "dismissed"):
                continue
            w += _SEV_W.get(str(v.get("severity") or "medium").lower(), 5)
        for s in ps:
            if str(s.get("state") or "open").lower() in ("resolved", "rotated"):
                continue
            w += _SEV_W.get(str(s.get("severity") or "high").lower(), 10) + 5
        for r in pr:
            w += _SEV_W.get(str(r.get("severity") or "medium").lower(), 4)
        by_repo[p] = {
            "open_security_findings": sum(1 for f in pf if str(f.get("state") or "open").lower() not in ("resolved", "fixed", "dismissed")),
            "open_vulnerabilities": sum(1 for v in pv if str(v.get("state") or "open").lower() not in ("resolved", "fixed", "dismissed")),
            "open_secret_exposures": sum(1 for s in ps if str(s.get("state") or "open").lower() not in ("resolved", "rotated")),
            "dependency_risk_rows": len(pr),
            "weighted_open_score": w,
        }

    by_initiative: dict[str, dict[str, Any]] = {}
    for f in findings:
        iid = str(f.get("initiative_id") or "").strip()
        if not iid:
            continue
        if iid not in by_initiative:
            by_initiative[iid] = {"finding_ids": [], "open_critical": 0, "open_high": 0}
        by_initiative[iid]["finding_ids"].append(str(f.get("finding_id") or ""))
        if str(f.get("state") or "open").lower() not in ("resolved", "fixed", "dismissed"):
            sev = str(f.get("severity") or "").lower()
            if sev == "critical":
                by_initiative[iid]["open_critical"] += 1
            elif sev == "high":
                by_initiative[iid]["open_high"] += 1

    by_release: dict[str, dict[str, Any]] = {}
    for f in findings:
        for rv in f.get("release_versions") or []:
            rs = str(rv)
            if not rs:
                continue
            if rs not in by_release:
                by_release[rs] = {"open_findings": 0, "finding_ids": []}
            if str(f.get("state") or "open").lower() not in ("resolved", "fixed", "dismissed"):
                by_release[rs]["open_findings"] += 1
                by_release[rs]["finding_ids"].append(str(f.get("finding_id") or ""))
    for v in vulns:
        for rv in v.get("release_versions") or []:
            rs = str(rv)
            if not rs:
                continue
            if rs not in by_release:
                by_release[rs] = {"open_findings": 0, "finding_ids": [], "open_vulnerabilities": 0}
            if str(v.get("state") or "open").lower() not in ("resolved", "fixed", "dismissed"):
                by_release[rs]["open_vulnerabilities"] = int(by_release[rs].get("open_vulnerabilities") or 0) + 1

    by_environment: dict[str, dict[str, Any]] = {}
    for block in doc.get("environment_posture") or []:
        if not isinstance(block, dict):
            continue
        eid = str(block.get("environment_id") or "")
        if not eid:
            continue
        by_environment[eid] = {
            "open_findings": int(block.get("open_findings") or 0),
            "last_scan_at": str(block.get("last_scan_at") or ""),
            "scan_tool": str(block.get("scan_tool") or ""),
        }

    return {
        "by_repo": by_repo,
        "by_initiative": by_initiative,
        "by_release": by_release,
        "by_environment": by_environment,
        "summary_counts": {
            "security_findings": _open_severity_counts(findings),
            "vulnerabilities": _open_severity_counts(vulns),
            "secret_exposures": _open_severity_counts(secrets),
        },
    }
