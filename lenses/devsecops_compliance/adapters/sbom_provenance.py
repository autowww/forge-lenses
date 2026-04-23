"""SBOM and provenance → ``sbom_component`` / ``provenance_attestation``."""

from __future__ import annotations

from typing import Any


def normalize_syft_package(raw: dict[str, Any], *, project: str = "", sbom_id: str = "") -> dict[str, Any]:
    return {
        "canonical_kind": "sbom_component",
        "component_id": str(raw.get("id") or raw.get("name") or "") + "@" + str(raw.get("version") or ""),
        "project": project,
        "sbom_id": sbom_id,
        "name": str(raw.get("name") or ""),
        "version": str(raw.get("version") or ""),
        "type": str(raw.get("type") or "library"),
        "purl": str(raw.get("purl") or ""),
        "licenses": raw.get("licenses") if isinstance(raw.get("licenses"), list) else [],
    }


def normalize_cosign_attestation(raw: dict[str, Any], *, project: str = "", artifact_ref: str = "") -> dict[str, Any]:
    return {
        "canonical_kind": "provenance_attestation",
        "attestation_id": str(raw.get("uuid") or raw.get("digest") or artifact_ref),
        "project": project,
        "provider": "cosign",
        "artifact_ref": artifact_ref,
        "predicate_type": str(raw.get("predicateType") or raw.get("predicate_type") or "https://slsa.dev/provenance/v1"),
        "signed_at": str(raw.get("integratedTime") or raw.get("signed_at") or ""),
        "verifier": str(raw.get("issuer") or ""),
        "valid": bool(raw.get("valid", True)),
    }
