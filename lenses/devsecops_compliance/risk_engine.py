"""Risk score from findings, secrets, dependencies, with exceptions and control mitigation."""

from __future__ import annotations

from typing import Any

_SEV_W = {"critical": 28, "high": 16, "medium": 7, "low": 3, "info": 0, "unknown": 5}


def _parse_iso(ts: str) -> str:
    return (ts or "").strip()


def _exception_active(exc: dict[str, Any], now_iso: str) -> bool:
    exp = _parse_iso(str(exc.get("expires_at") or ""))
    if exp and now_iso and exp < now_iso:
        return False
    return str(exc.get("status") or "active").lower() in ("active", "approved", "accepted")


def _covered_ids(exceptions: list[dict[str, Any]], now_iso: str) -> set[str]:
    out: set[str] = set()
    for e in exceptions:
        if not isinstance(e, dict) or not _exception_active(e, now_iso):
            continue
        for k in ("finding_ids", "vulnerability_ids", "exposure_ids"):
            for x in e.get(k) or []:
                out.add(str(x))
    return out


def compute_risk_score(doc: dict[str, Any], *, now_iso: str = "") -> dict[str, Any]:
    """Higher score = worse risk (0–100 cap). Based on open items minus active exceptions; controls reduce."""
    covered = _covered_ids([e for e in doc.get("exceptions") or [] if isinstance(e, dict)], now_iso)
    raw = 0
    breakdown: dict[str, int] = {
        "from_findings": 0,
        "from_vulnerabilities": 0,
        "from_secrets": 0,
        "from_dependency_risks": 0,
        "mitigation_controls": 0,
    }

    for f in doc.get("security_findings") or []:
        if not isinstance(f, dict):
            continue
        if str(f.get("state") or "open").lower() in ("dismissed", "resolved", "fixed"):
            continue
        fid = str(f.get("finding_id") or "")
        if fid in covered:
            continue
        sev = str(f.get("severity") or "medium").lower()
        w = _SEV_W.get(sev, 5)
        breakdown["from_findings"] += w
        raw += w

    for v in doc.get("vulnerabilities") or []:
        if not isinstance(v, dict):
            continue
        if str(v.get("state") or "open").lower() in ("dismissed", "resolved", "fixed"):
            continue
        vid = str(v.get("vuln_id") or "")
        if vid in covered:
            continue
        sev = str(v.get("severity") or "medium").lower()
        w = _SEV_W.get(sev, 5)
        breakdown["from_vulnerabilities"] += w
        raw += w

    for s in doc.get("secret_exposures") or []:
        if not isinstance(s, dict):
            continue
        if str(s.get("state") or "open").lower() in ("resolved", "rotated"):
            continue
        eid = str(s.get("exposure_id") or "")
        if eid in covered:
            continue
        sev = str(s.get("severity") or "high").lower()
        w = _SEV_W.get(sev, 10) + 5
        breakdown["from_secrets"] += w
        raw += w

    for d in doc.get("dependency_risks") or []:
        if not isinstance(d, dict):
            continue
        rid = str(d.get("risk_id") or "")
        if rid in covered:
            continue
        sev = str(d.get("severity") or "medium").lower()
        w = _SEV_W.get(sev, 4)
        breakdown["from_dependency_risks"] += w
        raw += w

    mit = 0
    ctx_release = str((doc.get("policy_context") or {}).get("release_version") or "")
    for c in doc.get("controls") or []:
        if not isinstance(c, dict):
            continue
        if str(c.get("implementation_status") or "").lower() != "implemented":
            continue
        rels = c.get("applies_to_releases") or []
        if isinstance(rels, list) and ctx_release and ctx_release not in [str(x) for x in rels]:
            continue
        eff = int(c.get("risk_mitigation_points") or 8)
        mit += eff
    breakdown["mitigation_controls"] = mit
    raw = max(0, raw - mit)

    value = min(100, raw)
    return {
        "value": value,
        "scale": "0-100 (higher is worse)",
        "computed_from": "open findings, vulnerabilities, secret exposures, dependency risks; minus active control mitigation; exceptions exclude listed ids",
        "breakdown": breakdown,
        "exception_count_active": sum(1 for e in doc.get("exceptions") or [] if isinstance(e, dict) and _exception_active(e, now_iso)),
    }
