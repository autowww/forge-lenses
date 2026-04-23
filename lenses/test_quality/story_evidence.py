"""Resolve test / quality evidence for a WBS story id from the local fixture."""

from __future__ import annotations

from pathlib import Path
from typing import Any


def story_quality_evidence_from_doc(doc: dict[str, Any], wbs_story_id: str) -> dict[str, Any]:
    sid = (wbs_story_id or "").strip()
    if not sid:
        return {"ok": False, "error": "missing_story_id"}

    cases: list[dict[str, Any]] = []
    for tc in doc.get("test_cases") or []:
        if not isinstance(tc, dict):
            continue
        ids = tc.get("story_ids")
        if isinstance(ids, list) and sid in [str(x) for x in ids]:
            cases.append(tc)

    defects_out: list[dict[str, Any]] = []
    for d in doc.get("defects") or []:
        if not isinstance(d, dict):
            continue
        ids = d.get("story_ids")
        if isinstance(ids, list) and sid in [str(x) for x in ids]:
            defects_out.append(d)

    suite_ids = {str(c.get("suite_id")) for c in cases if c.get("suite_id")}
    runs_out: list[dict[str, Any]] = []
    for r in doc.get("test_runs") or []:
        if not isinstance(r, dict):
            continue
        if str(r.get("suite_id") or "") in suite_ids:
            runs_out.append(r)
    runs_out.sort(key=lambda x: str(x.get("finished_at") or x.get("started_at") or ""), reverse=True)

    uat = [
        u
        for u in doc.get("uat_signoffs") or []
        if isinstance(u, dict) and str(u.get("story_id") or "") == sid
    ]

    evidence = [
        e
        for e in doc.get("evidence_attachments") or []
        if isinstance(e, dict) and str(e.get("story_id") or "") == sid
    ]

    return {
        "ok": True,
        "story_id": sid,
        "test_cases": cases,
        "test_runs_preview": runs_out[:8],
        "defects": defects_out,
        "uat_signoffs": uat,
        "evidence_attachments": evidence,
    }


def load_doc_for_workspace(workspace_root: Path, lenses_root: Path) -> dict[str, Any] | None:
    from lenses.test_quality.local_store import load_demo_fixture, read_local_test_quality
    import os

    doc = read_local_test_quality(workspace_root)
    if doc is not None:
        return doc
    raw = (os.environ.get("LENSES_TEST_QUALITY_SEED_DEMO") or "").strip().lower()
    if raw in ("1", "true", "yes", "on"):
        return load_demo_fixture(lenses_root)
    return None
