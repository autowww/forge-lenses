"""Public session view for Studio API and SSE."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from lenses.doc_management import session_store as store
from lenses.doc_management.manifest import load_manifest


def _read_tail(path: Path, limit: int = 12000) -> str | None:
    if not path.is_file():
        return None
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return None
    return text if len(text) <= limit else text[:limit] + "\n…(truncated)"


def _pack_artifacts(workspace_root: Path, session_id: str) -> list[dict[str, Any]]:
    pack = store.pack_dir(workspace_root, session_id)
    if not pack.is_dir():
        return []
    rows: list[dict[str, Any]] = []
    for child in sorted(pack.iterdir()):
        if not child.is_dir():
            continue
        arts: list[str] = []
        for name in (
            "hydration-brief.md",
            "claim-inventory.json",
            "hydration-result.json",
            "route-confidence.json",
            "workcell_result.json",
        ):
            if (child / name).is_file() or (child / "workcell-out").joinpath(name).is_file():
                arts.append(name)
        brief_path = child / "hydration-brief.md"
        if not brief_path.is_file():
            wc = child / "workcell-out"
            for arun in sorted(wc.glob("arun_*")) if wc.is_dir() else []:
                bp = arun / "hydration-brief.md"
                if bp.is_file():
                    brief_path = bp
                    break
        rows.append(
            {
                "slug": child.name,
                "artifacts": arts,
                "hydration_brief_markdown": _read_tail(brief_path, 8000) if brief_path.is_file() else None,
            }
        )
    return rows


def session_public_view(workspace_root: Path, session_id: str) -> dict[str, Any] | None:
    sess = store.load_session(workspace_root, session_id)
    if not sess:
        return None
    out = dict(sess)
    out["pack_artifacts"] = _pack_artifacts(workspace_root, session_id)
    out["reviewer_decision_manifest"] = load_manifest(workspace_root, session_id)
    out["session_href"] = f"/doc-management/session/{session_id}"
    return out
