"""Expand optional ``ingestions[]`` using vendor adapters."""

from __future__ import annotations

from typing import Any

from lenses.devsecops_compliance.adapters import (
    normalize_codeql_alert,
    normalize_cosign_attestation,
    normalize_dependabot_alert,
    normalize_gitleaks_finding,
    normalize_semgrep_result,
    normalize_syft_package,
    normalize_trivy_misconfig,
    normalize_trivy_vulnerability,
)


def expand_ingestions(doc: dict[str, Any]) -> dict[str, Any]:
    out = dict(doc)
    findings = [f for f in out.get("security_findings") or [] if isinstance(f, dict)]
    vulns = [v for v in out.get("vulnerabilities") or [] if isinstance(v, dict)]
    secrets = [s for s in out.get("secret_exposures") or [] if isinstance(s, dict)]
    risks = [r for r in out.get("dependency_risks") or [] if isinstance(r, dict)]
    sbom = [b for b in out.get("sbom_components") or [] if isinstance(b, dict)]
    prov = [p for p in out.get("provenance_attestations") or [] if isinstance(p, dict)]

    for ing in doc.get("ingestions") or []:
        if not isinstance(ing, dict):
            continue
        prov_name = str(ing.get("provider") or "").strip().lower()
        proj = str(ing.get("project") or "")
        payload = ing.get("payload")
        if not isinstance(payload, dict):
            continue
        if prov_name == "codeql":
            findings.append(normalize_codeql_alert(payload, project=proj))
        elif prov_name == "semgrep":
            findings.append(normalize_semgrep_result(payload, project=proj))
        elif prov_name == "dependabot":
            vulns.append(normalize_dependabot_alert(payload, project=proj))
        elif prov_name == "gitleaks":
            secrets.append(normalize_gitleaks_finding(payload, project=proj))
        elif prov_name == "trivy_vuln":
            findings.append(
                normalize_trivy_vulnerability(payload, project=proj, artifact=str(ing.get("artifact") or ""))
            )
        elif prov_name == "trivy_iac":
            findings.append(normalize_trivy_misconfig(payload, project=proj, file_path=str(ing.get("file") or "")))
        elif prov_name == "syft":
            sbom.append(normalize_syft_package(payload, project=proj, sbom_id=str(ing.get("sbom_id") or "")))
        elif prov_name == "cosign":
            prov.append(
                normalize_cosign_attestation(
                    payload, project=proj, artifact_ref=str(ing.get("artifact_ref") or "")
                )
            )

    out["security_findings"] = findings
    out["vulnerabilities"] = vulns
    out["secret_exposures"] = secrets
    out["dependency_risks"] = risks
    out["sbom_components"] = sbom
    out["provenance_attestations"] = prov
    return out
