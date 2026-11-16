"""Fixture-backed DevSecOps rows for a WBS story id."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from lenses.devsecops_compliance.ingest import expand_ingestions
from lenses.devsecops_compliance.local_store import load_demo_fixture, read_local_devsecops_compliance


def load_doc_for_workspace(workspace_root: Path, lenses_root: Path) -> dict[str, Any] | None:
    import os

    doc = read_local_devsecops_compliance(workspace_root)
    if doc is not None:
        return doc
    raw = (os.environ.get("LENSES_DEVSECOPS_COMPLIANCE_SEED_DEMO") or "").strip().lower()
    if raw in ("1", "true", "yes", "on"):
        return load_demo_fixture(lenses_root)
    return None


def story_devsecops_evidence_from_doc(doc: dict[str, Any], wbs_story_id: str) -> dict[str, Any]:
    sid = (wbs_story_id or "").strip()
    if not sid:
        return {"ok": False, "error": "missing_story_id"}

    doc = expand_ingestions(doc)

    def has_story(row: dict[str, Any]) -> bool:
        ids = row.get("story_ids")
        return isinstance(ids, list) and sid in [str(x) for x in ids]

    findings = [f for f in doc.get("security_findings") or [] if isinstance(f, dict) and has_story(f)]
    vulns = [v for v in doc.get("vulnerabilities") or [] if isinstance(v, dict) and has_story(v)]
    secrets = [s for s in doc.get("secret_exposures") or [] if isinstance(s, dict) and has_story(s)]

    finding_ids = {str(f.get("finding_id") or "") for f in findings}
    exceptions = [
        e
        for e in doc.get("exceptions") or []
        if isinstance(e, dict)
        and (
            finding_ids.intersection({str(x) for x in (e.get("finding_ids") or [])})
            or sid in [str(x) for x in (e.get("story_ids") or [])]
        )
    ]

    controls = [c for c in doc.get("controls") or [] if isinstance(c, dict) and sid in [str(x) for x in (c.get("story_ids") or [])]]

    return {
        "ok": True,
        "story_id": sid,
        "security_findings": findings,
        "vulnerabilities": vulns,
        "secret_exposures": secrets,
        "exceptions": exceptions,
        "controls": controls,
    }
