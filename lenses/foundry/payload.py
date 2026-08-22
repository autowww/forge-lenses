"""Normalize Dark Factory machine artifacts into a Studio-friendly run payload."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

STAGE_ORDER = (
    "classify",
    "route",
    "context",
    "plan",
    "draft",
    "apply+verify",
    "assay",
    "promote",
)


def _read_json(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return data if isinstance(data, dict) else None


def _map_phase_status(raw: str) -> str:
    s = (raw or "").strip().lower()
    if s in ("ok", "pass", "completed", "finished"):
        return "completed"
    if s in ("fail", "failed", "error"):
        return "failed"
    if s in ("escalated", "blocked"):
        return "blocked"
    if s in ("running", "in_progress"):
        return "in_progress"
    return "not_started"


def normalize_phases(phases_raw: list[Any] | None) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    seen: set[str] = set()
    if phases_raw:
        for item in phases_raw:
            if not isinstance(item, dict):
                continue
            name = str(item.get("name") or item.get("phase") or "").strip()
            if not name:
                continue
            seen.add(name)
            out.append(
                {
                    "id": name,
                    "label": name,
                    "status": _map_phase_status(str(item.get("status") or "")),
                    "detail": str(item.get("detail") or item.get("message") or "")[:500],
                }
            )
    for name in STAGE_ORDER:
        if name not in seen:
            out.append({"id": name, "label": name, "status": "not_started", "detail": ""})
    return out


def normalize_run_dir(run_dir: Path) -> dict[str, Any]:
    machine = run_dir / "machine"
    run_meta = _read_json(machine / "run.json") or {}
    phases_doc = _read_json(machine / "phases.json") or {}
    assay = _read_json(machine / "assay.json") or {}
    proof = _read_json(machine / "proof.json") or {}
    promote = _read_json(machine / "promote.json") or {}

    phases_list = phases_doc.get("phases") if isinstance(phases_doc.get("phases"), list) else phases_doc
    if not isinstance(phases_list, list):
        phases_list = []

    final_status = str(run_meta.get("final_status") or run_meta.get("status") or "unknown")
    return {
        "run_dir": str(run_dir),
        "goal": str(run_meta.get("goal") or ""),
        "target": str(run_meta.get("target") or ""),
        "level": str(run_meta.get("level") or "L1"),
        "final_status": final_status,
        "tier": str(run_meta.get("tier") or ""),
        "phases": normalize_phases(phases_list),
        "assay": assay,
        "proof": proof,
        "promote": promote,
        "assay_ok": bool(assay.get("ok")) if assay else None,
    }


def capabilities_payload() -> dict[str, Any]:
    return {
        "ok": True,
        "ladder": {
            "L1": {"status": "available", "label": "Function-level (pytest gate)"},
            "L2": {"status": "stub", "label": "Change-set (not wired in Studio)"},
            "L3": {"status": "stub", "label": "Use-case slice (not wired in Studio)"},
            "L4": {"status": "not_planned", "label": "Beyond PoC scope"},
        },
    }
