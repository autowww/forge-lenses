"""Vendor-shaped payloads → canonical DevSecOps rows."""

from lenses.devsecops_compliance.adapters.code_scanning import normalize_codeql_alert, normalize_semgrep_result
from lenses.devsecops_compliance.adapters.container_iac import normalize_trivy_misconfig, normalize_trivy_vulnerability
from lenses.devsecops_compliance.adapters.dependency_scan import normalize_dependabot_alert, normalize_snyk_issue
from lenses.devsecops_compliance.adapters.secret_scan import normalize_gitleaks_finding
from lenses.devsecops_compliance.adapters.sbom_provenance import normalize_cosign_attestation, normalize_syft_package

__all__ = [
    "normalize_codeql_alert",
    "normalize_semgrep_result",
    "normalize_dependabot_alert",
    "normalize_snyk_issue",
    "normalize_gitleaks_finding",
    "normalize_trivy_vulnerability",
    "normalize_trivy_misconfig",
    "normalize_syft_package",
    "normalize_cosign_attestation",
]
