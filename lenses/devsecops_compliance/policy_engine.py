"""Policy-as-code style checks for release / promotion readiness."""

from __future__ import annotations

from typing import Any

from lenses.devsecops_compliance.risk_engine import compute_risk_score


def evaluate_security_policy_checks(doc: dict[str, Any], *, now_iso: str = "") -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    risk = compute_risk_score(doc, now_iso=now_iso)
    ctx = doc.get("policy_context") if isinstance(doc.get("policy_context"), dict) else {}
    release_v = str(ctx.get("release_version") or "")
    project = str(ctx.get("project") or "")

    findings = [f for f in doc.get("security_findings") or [] if isinstance(f, dict)]
    vulns = [v for v in doc.get("vulnerabilities") or [] if isinstance(v, dict)]
    secrets = [s for s in doc.get("secret_exposures") or [] if isinstance(s, dict)]
    sbom = [x for x in doc.get("sbom_components") or [] if isinstance(x, dict)]
    prov = [x for x in doc.get("provenance_attestations") or [] if isinstance(x, dict)]

    covered = set()
    for e in doc.get("exceptions") or []:
        if not isinstance(e, dict):
            continue
        exp = str(e.get("expires_at") or "")
        if exp and now_iso and exp < now_iso:
            continue
        if str(e.get("status") or "").lower() not in ("active", "approved", "accepted", ""):
            continue
        for k in ("finding_ids", "vulnerability_ids", "exposure_ids"):
            for x in e.get(k) or []:
                covered.add(str(x))

    def open_critical_items() -> int:
        n = 0
        for f in findings:
            if str(f.get("state") or "open").lower() in ("resolved", "fixed", "dismissed"):
                continue
            if str(f.get("severity") or "").lower() != "critical":
                continue
            if str(f.get("finding_id") or "") in covered:
                continue
            n += 1
        for v in vulns:
            if str(v.get("state") or "open").lower() in ("resolved", "fixed", "dismissed"):
                continue
            if str(v.get("severity") or "").lower() != "critical":
                continue
            if str(v.get("vuln_id") or "") in covered:
                continue
            n += 1
        return n

    for rule in doc.get("security_policies") or []:
        if not isinstance(rule, dict):
            continue
        rid = str(rule.get("id") or "")
        name = str(rule.get("name") or rid)
        rtype = str(rule.get("type") or "").strip()
        passed = True
        detail = ""

        if rtype == "max_open_critical_without_exception":
            max_n = int(rule.get("max") or 0)
            n = open_critical_items()
            passed = n <= max_n
            detail = f"{n} critical item(s) without active exception (max {max_n})"
        elif rtype == "max_risk_score":
            max_r = int(rule.get("max_score") or 100)
            passed = int(risk.get("value") or 0) <= max_r
            detail = f"Risk score {risk.get('value')} (max {max_r})"
        elif rtype == "sbom_components_minimum":
            need = int(rule.get("min_count") or 1)
            proj_sbom = [x for x in sbom if not project or str(x.get("project") or "") == project]
            passed = len(proj_sbom) >= need
            detail = f"{len(proj_sbom)} SBOM component(s) (min {need})"
        elif rtype == "provenance_attestation_present":
            need_valid = bool(rule.get("require_valid", True))
            proj_p = [x for x in prov if not project or str(x.get("project") or "") == project]
            if need_valid:
                proj_p = [x for x in proj_p if x.get("valid")]
            passed = len(proj_p) >= int(rule.get("min_count") or 1)
            detail = f"{len(proj_p)} provenance attestation(s)"
        elif rtype == "no_open_high_secrets":
            bad = [
                s
                for s in secrets
                if str(s.get("state") or "open").lower() not in ("resolved", "rotated")
                and str(s.get("severity") or "").lower() in ("high", "critical")
                and str(s.get("exposure_id") or "") not in covered
            ]
            passed = len(bad) == 0
            detail = f"{len(bad)} high/critical secret exposure(s) without exception"
        else:
            passed = True
            detail = "Unknown rule; not enforced"

        applies = rule.get("applies_to_environments") or []
        envs = [str(x) for x in applies] if isinstance(applies, list) else []
        blocks_train = bool(rule.get("blocks_release_train"))

        out.append(
            {
                "policy_id": rid,
                "name": name,
                "passed": passed,
                "detail": detail,
                "applies_to_environments": envs,
                "blocks_release_train": blocks_train,
            }
        )

    return out


def security_policy_promotion_blockers(
    evaluations: list[dict[str, Any]],
    promotions: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    seen: set[str] = set()
    for prom in promotions:
        if not isinstance(prom, dict):
            continue
        pid = str(prom.get("id") or "")
        to_env = str(prom.get("to_env") or "")
        if not pid or not to_env:
            continue
        for ev in evaluations:
            if ev.get("passed"):
                continue
            envs = ev.get("applies_to_environments") or []
            if isinstance(envs, list) and envs and to_env not in envs:
                continue
            key = f"{pid}:security_policy:{ev.get('policy_id')}"
            if key in seen:
                continue
            seen.add(key)
            rows.append(
                {
                    "promotion_id": pid,
                    "reason": f"security_policy_failed:{ev.get('policy_id')}",
                    "detail": f"{ev.get('name')}: {ev.get('detail')}",
                }
            )
    return rows
