"""Reviewer decision manifest writeback for Doc Management sessions."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from lenses.doc_management import session_store as store

_MANIFEST_SCHEMA = "forge.reviewer_decision_manifest.v1"
_VALID_DECISIONS = frozenset(
    {
        "promote_as_is",
        "promote_after_edit",
        "split_seed",
        "route_elsewhere",
        "patch_canonical_only",
        "reject",
        "hold_for_evidence",
    }
)


def manifest_path(workspace_root: Path, session_id: str) -> Path:
    return store.pack_dir(workspace_root, session_id) / "reviewer-decision-manifest.json"


def write_manifest(
    workspace_root: Path,
    session_id: str,
    *,
    reviewer: str,
    decisions: list[dict[str, Any]],
    hydration_plan_id: str | None = None,
) -> dict[str, Any]:
    sess = store.load_session(workspace_root, session_id)
    if not sess:
        raise ValueError("session_not_found")
    cleaned: list[dict[str, Any]] = []
    for row in decisions:
        if not isinstance(row, dict):
            continue
        decision = str(row.get("decision") or "").strip()
        if decision not in _VALID_DECISIONS:
            raise ValueError(f"invalid_decision:{decision}")
        target = str(row.get("target") or "").strip()
        if not target:
            raise ValueError("missing_target")
        cleaned.append(
            {
                "target": target,
                "decision": decision,
                "surfaces": row.get("surfaces") if isinstance(row.get("surfaces"), list) else [],
                "notes": str(row.get("notes") or "")[:4000],
            }
        )
    if not cleaned:
        raise ValueError("no_decisions")
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    manifest = {
        "schema": _MANIFEST_SCHEMA,
        "manifest_id": f"forge.rdm.{stamp}.{session_id[:12]}",
        "pack_id": session_id,
        "hydration_plan_id": hydration_plan_id,
        "reviewer": reviewer.strip() or "studio_operator",
        "decided_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "decisions": cleaned,
        "promotion_evidence": {"commits": [], "builds_run": [], "deploys": []},
    }
    p = manifest_path(workspace_root, session_id)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")
    sess["reviewer_manifest_path"] = str(p.relative_to(store.session_dir(workspace_root, session_id)))
    workflow = sess.setdefault("workflow", {})
    if isinstance(workflow, dict):
        workflow["stage"] = "review"
        completed = workflow.get("stages_completed")
        if isinstance(completed, list) and "review" not in completed:
            completed.append("review")
    store.append_event(sess, {"type": "manifest_saved", "title": "Reviewer manifest saved", "decision_count": len(cleaned)})
    store.save_session(workspace_root, sess)
    return manifest


def load_manifest(workspace_root: Path, session_id: str) -> dict[str, Any] | None:
    p = manifest_path(workspace_root, session_id)
    if not p.is_file():
        return None
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
