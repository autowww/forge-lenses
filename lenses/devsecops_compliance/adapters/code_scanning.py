"""Code scanning (SAST) → canonical ``security_finding``."""

from __future__ import annotations

from typing import Any


def normalize_codeql_alert(raw: dict[str, Any], *, project: str = "") -> dict[str, Any]:
    rule = raw.get("rule") if isinstance(raw.get("rule"), dict) else {}
    loc = raw.get("location") if isinstance(raw.get("location"), dict) else {}
    return {
        "canonical_kind": "security_finding",
        "finding_id": str(raw.get("id") or raw.get("number") or ""),
        "project": project,
        "provider": "codeql",
        "category": "sast",
        "severity": str(raw.get("severity") or rule.get("severity") or "medium").lower(),
        "state": str(raw.get("state") or "open").lower(),
        "title": str(raw.get("title") or rule.get("name") or "Code finding"),
        "rule_id": str(rule.get("id") or ""),
        "file_path": str(loc.get("path") or raw.get("path") or ""),
        "url": str(raw.get("html_url") or raw.get("url") or ""),
        "detected_at": str(raw.get("created_at") or ""),
    }


def normalize_semgrep_result(raw: dict[str, Any], *, project: str = "") -> dict[str, Any]:
    extra = raw.get("extra") if isinstance(raw.get("extra"), dict) else {}
    sev = str(extra.get("severity") or raw.get("severity") or "medium").lower()
    return {
        "canonical_kind": "security_finding",
        "finding_id": str(raw.get("check_id") or raw.get("id") or ""),
        "project": project,
        "provider": "semgrep",
        "category": "sast",
        "severity": sev,
        "state": "open",
        "title": str(extra.get("message") or raw.get("message") or "Semgrep finding"),
        "rule_id": str(raw.get("check_id") or ""),
        "file_path": str(raw.get("path") or ""),
        "url": "",
        "detected_at": "",
    }
