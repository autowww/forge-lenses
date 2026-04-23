"""Fixture-backed ops rows for a WBS story id."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from lenses.ops_delivery.ingest import expand_ingestions
from lenses.ops_delivery.local_store import load_demo_fixture, read_local_ops_delivery


def load_doc_for_workspace(workspace_root: Path, lenses_root: Path) -> dict[str, Any] | None:
    import os

    doc = read_local_ops_delivery(workspace_root)
    if doc is not None:
        return doc
    raw = (os.environ.get("LENSES_OPS_DELIVERY_SEED_DEMO") or "").strip().lower()
    if raw in ("1", "true", "yes", "on"):
        return load_demo_fixture(lenses_root)
    return None


def story_ops_delivery_evidence_from_doc(doc: dict[str, Any], wbs_story_id: str) -> dict[str, Any]:
    sid = (wbs_story_id or "").strip()
    if not sid:
        return {"ok": False, "error": "missing_story_id"}

    doc = expand_ingestions(doc)

    incidents = [
        i
        for i in doc.get("incidents") or []
        if isinstance(i, dict) and sid in [str(x) for x in (i.get("linked_story_ids") or [])]
    ]
    pms = []
    for p in doc.get("postmortems") or []:
        if not isinstance(p, dict):
            continue
        wids = p.get("linked_story_ids") or p.get("linked_work_item_ids") or []
        if isinstance(wids, list) and sid in [str(x) for x in wids]:
            pms.append(p)

    slos = [s for s in doc.get("slos") or [] if isinstance(s, dict) and sid in [str(x) for x in (s.get("story_ids") or [])]]

    return {
        "ok": True,
        "story_id": sid,
        "incidents": incidents,
        "postmortems": pms,
        "slos": slos,
    }
