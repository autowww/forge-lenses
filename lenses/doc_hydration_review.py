"""Read-only doc-hydration review pack surface (Hydration v2, Phase 5).

Presents hydration run artifacts — ``hydration-brief.md``,
``claim-inventory.json``, hydration plans, ``workcell_result.json``, and the
``reviewer-decision-manifest.json`` approval record — from known workspace
locations. Read-only by design: approval writeback is a later increment; the
manifest file itself stays owned by the forge-platform promotion flow.

Scanned roots (relative to the Lenses workspace root):

- ``forge-platform/docs/hydration-runs/<pack>/``
- ``workbench/doc-hydration-runs/**/arun_*/`` (workcell outputs)
- extra colon-separated roots via ``LENSES_DOC_HYDRATION_ROOTS``
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Callable

SendJson = Callable[[int, dict[str, Any]], None]

_ARTIFACT_FILES = (
    "hydration-brief.md",
    "claim-inventory.json",
    "reviewer-decision-manifest.json",
    "workcell_result.json",
    "route-confidence.json",
    "agent_run.json",
)
_MAX_PACKS = 200


def _candidate_roots(workspace_root: Path) -> list[tuple[str, Path]]:
    roots: list[tuple[str, Path]] = [
        ("forge-platform", workspace_root / "forge-platform" / "docs" / "hydration-runs"),
        ("workbench", workspace_root / "workbench" / "doc-hydration-runs"),
    ]
    extra = os.environ.get("LENSES_DOC_HYDRATION_ROOTS", "").strip()
    if extra:
        for i, raw in enumerate(p for p in extra.split(":") if p.strip()):
            roots.append((f"extra{i}", Path(raw).expanduser()))
    return roots


def _is_pack_dir(path: Path) -> bool:
    return any((path / name).is_file() for name in _ARTIFACT_FILES)


def _iter_pack_dirs(workspace_root: Path) -> list[tuple[str, Path]]:
    """Return (pack_id, dir) pairs; pack_id is ``<source>:<dirname>``."""
    packs: list[tuple[str, Path]] = []
    for source, root in _candidate_roots(workspace_root):
        if not root.is_dir():
            continue
        for child in sorted(root.iterdir()):
            if not child.is_dir():
                continue
            if _is_pack_dir(child):
                packs.append((f"{source}:{child.name}", child))
            else:
                # workcell out-dirs nest arun_* run roots one level deeper
                for run_dir in sorted(child.glob("arun_*")):
                    if run_dir.is_dir() and _is_pack_dir(run_dir):
                        packs.append((f"{source}:{child.name}/{run_dir.name}", run_dir))
            if len(packs) >= _MAX_PACKS:
                return packs
    return packs


def _read_json(path: Path) -> Any | None:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def _pack_summary(pack_id: str, pack_dir: Path) -> dict[str, Any]:
    inventory = _read_json(pack_dir / "claim-inventory.json")
    manifest = _read_json(pack_dir / "reviewer-decision-manifest.json")
    result = _read_json(pack_dir / "workcell_result.json")
    claim_count = None
    if isinstance(inventory, dict):
        claims = inventory.get("claims")
        if isinstance(claims, list):
            claim_count = len(claims)
    decisions = None
    if isinstance(manifest, dict):
        entries = manifest.get("decisions")
        if isinstance(entries, list):
            decisions = len(entries)
    return {
        "pack_id": pack_id,
        "path": str(pack_dir),
        "artifacts": sorted(p.name for p in pack_dir.iterdir() if p.is_file()),
        "has_brief": (pack_dir / "hydration-brief.md").is_file(),
        "claim_count": claim_count,
        "reviewer_decisions": decisions,
        "workcell_status": result.get("status") if isinstance(result, dict) else None,
        "forge_run_id": result.get("forge_run_id") if isinstance(result, dict) else None,
    }


def build_review_pack_list(workspace_root: Path) -> dict[str, Any]:
    packs = [_pack_summary(pid, pdir) for pid, pdir in _iter_pack_dirs(workspace_root)]
    return {"ok": True, "read_only": True, "count": len(packs), "packs": packs}


def build_review_pack_detail(workspace_root: Path, pack_id: str) -> dict[str, Any]:
    for pid, pack_dir in _iter_pack_dirs(workspace_root):
        if pid != pack_id:
            continue
        detail: dict[str, Any] = {
            "ok": True,
            "read_only": True,
            "pack": _pack_summary(pid, pack_dir),
            "claim_inventory": _read_json(pack_dir / "claim-inventory.json"),
            "reviewer_decision_manifest": _read_json(pack_dir / "reviewer-decision-manifest.json"),
            "workcell_result": _read_json(pack_dir / "workcell_result.json"),
            "agent_run": _read_json(pack_dir / "agent_run.json"),
        }
        brief = pack_dir / "hydration-brief.md"
        if brief.is_file():
            try:
                detail["hydration_brief_markdown"] = brief.read_text(encoding="utf-8")
            except OSError:
                detail["hydration_brief_markdown"] = None
        plans = sorted(pack_dir.glob("hydration_plan*.json"))
        if plans:
            detail["hydration_plans"] = [_read_json(p) for p in plans]
        return detail
    return {"ok": False, "error": "review_pack_not_found"}


def get_review_packs(workspace_root: Path, *, send_json: SendJson) -> None:
    send_json(200, build_review_pack_list(workspace_root))


def get_review_pack_detail(workspace_root: Path, pack_id: str, *, send_json: SendJson) -> None:
    payload = build_review_pack_detail(workspace_root, pack_id)
    send_json(200 if payload.get("ok") else 404, payload)
