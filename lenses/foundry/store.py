"""JSON file store for Foundry runs under workspace .lenses-local."""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def runs_root(workspace_root: Path) -> Path:
    return workspace_root / ".lenses-local" / "foundry-runs"


def new_run_id() -> str:
    return f"frun_{uuid.uuid4().hex[:12]}"


def run_record_path(workspace_root: Path, run_id: str) -> Path:
    return runs_root(workspace_root) / f"{run_id}.json"


def load_run(workspace_root: Path, run_id: str) -> dict[str, Any] | None:
    path = run_record_path(workspace_root, run_id)
    if not path.is_file():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return data if isinstance(data, dict) else None


def save_run(workspace_root: Path, record: dict[str, Any]) -> None:
    rid = str(record.get("id") or "").strip()
    if not rid:
        raise ValueError("run record missing id")
    root = runs_root(workspace_root)
    root.mkdir(parents=True, exist_ok=True)
    path = run_record_path(workspace_root, rid)
    path.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")


def list_runs(workspace_root: Path) -> list[dict[str, Any]]:
    root = runs_root(workspace_root)
    if not root.is_dir():
        return []
    out: list[dict[str, Any]] = []
    for path in sorted(root.glob("frun_*.json"), key=lambda p: p.stat().st_mtime, reverse=True):
        data = load_run(workspace_root, path.stem)
        if data:
            out.append(data)
    return out


def create_run_record(
    *,
    goal: str,
    target: str,
    level: str,
    execution_mode: str,
    project: str = "",
    plan: dict[str, Any] | None = None,
) -> dict[str, Any]:
    rid = new_run_id()
    return {
        "id": rid,
        "created_at": _now_iso(),
        "updated_at": _now_iso(),
        "goal": goal,
        "target": target,
        "level": level,
        "execution_mode": execution_mode,
        "project": project,
        "status": "created",
        "foundry_run_dir": "",
        "phases": [],
        "plan": plan or {},
        "assay_ok": None,
        "final_status": "",
        "promoted": False,
        "approved": False,
    }


def touch_run(record: dict[str, Any], **fields: Any) -> dict[str, Any]:
    record = dict(record)
    record.update(fields)
    record["updated_at"] = _now_iso()
    return record
