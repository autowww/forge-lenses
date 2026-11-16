"""Secret scanning → ``secret_exposure``."""

from __future__ import annotations

from typing import Any


def normalize_gitleaks_finding(raw: dict[str, Any], *, project: str = "") -> dict[str, Any]:
    return {
        "canonical_kind": "secret_exposure",
        "exposure_id": str(raw.get("Match") or raw.get("match") or raw.get("id") or ""),
        "project": project,
        "provider": "gitleaks",
        "rule_id": str(raw.get("RuleID") or raw.get("rule_id") or ""),
        "severity": str(raw.get("severity") or "high").lower(),
        "state": str(raw.get("state") or "open").lower(),
        "file_path": str(raw.get("File") or raw.get("file") or ""),
        "line": raw.get("StartLine") or raw.get("line"),
        "redacted_preview": str(raw.get("Description") or raw.get("description") or "secret"),
        "detected_at": str(raw.get("Date") or raw.get("date") or ""),
    }
