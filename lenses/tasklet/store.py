"""JSON persistence for TaskletRun under ``.lenses-local/tasklet-runs/``."""

from __future__ import annotations

import json
import os
import uuid
from pathlib import Path
from typing import Any

from lenses.docs_health import store as dh_store
from lenses.tasklet.state_machine import normalize_run_record


def _runs_dir(workspace_root: Path) -> Path:
    d = workspace_root.resolve() / ".lenses-local" / "tasklet-runs"
    d.mkdir(parents=True, exist_ok=True)
    try:
        os.chmod(d.parent.parent, 0o700)
        os.chmod(d.parent, 0o700)
        os.chmod(d, 0o700)
    except OSError:
        pass
    return d


def _now() -> str:
    return dh_store.now_iso()


def create_tasklet_run(
    workspace_root: Path,
    *,
    tasklet_id: str,
    tasklet_version: int,
    kind: str,
    project_slug: str,
    docs_health_session_id: str | None = None,
    agent_runtime_session_id: str | None = None,
    sandbox_backend: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    rid = uuid.uuid4().hex
    ts = _now()
    rec: dict[str, Any] = {
        "id": rid,
        "tasklet_id": str(tasklet_id or "").strip(),
        "tasklet_version": int(tasklet_version),
        "kind": str(kind or "").strip(),
        "project_slug": str(project_slug or "").strip(),
        "state": "created",
        "stop_reason": None,
        "last_error": None,
        "docs_health_session_id": docs_health_session_id,
        "agent_runtime_session_id": agent_runtime_session_id,
        "created_at": ts,
        "updated_at": ts,
        "checkpoints": [],
        "artifacts": [],
        "event_seq": 0,
        "sandbox_backend": sandbox_backend,
        "sandbox_handle": None,
    }
    if metadata:
        rec["metadata"] = metadata
    write_tasklet_run(workspace_root, rec)
    return rec


def tasklet_run_path(workspace_root: Path, run_id: str) -> Path:
    safe = str(run_id or "").strip().replace(os.sep, "_").replace("/", "_")
    if not safe or ".." in safe:
        raise ValueError("invalid_tasklet_run_id")
    return _runs_dir(workspace_root) / f"{safe}.json"


def write_tasklet_run(workspace_root: Path, rec: dict[str, Any]) -> None:
    rid = str(rec.get("id") or "").strip()
    if not rid:
        raise ValueError("tasklet_run_id_required")
    rec["updated_at"] = _now()
    p = tasklet_run_path(workspace_root, rid)
    p.write_text(json.dumps(rec, indent=2, sort_keys=True), encoding="utf-8")
    try:
        os.chmod(p, 0o600)
    except OSError:
        pass


def load_tasklet_run(workspace_root: Path, run_id: str) -> dict[str, Any] | None:
    p = tasklet_run_path(workspace_root, run_id)
    if not p.is_file():
        return None
    try:
        raw = json.loads(p.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(raw, dict):
        return None
    return normalize_run_record(raw)


def update_tasklet_run(workspace_root: Path, run_id: str, **patch: Any) -> dict[str, Any] | None:
    cur = load_tasklet_run(workspace_root, run_id)
    if not cur:
        return None
    for k, v in patch.items():
        if v is not None or k in cur:
            cur[k] = v
    write_tasklet_run(workspace_root, cur)
    return load_tasklet_run(workspace_root, run_id)


def append_checkpoint(
    workspace_root: Path,
    run_id: str,
    *,
    step: str,
    note: str | None = None,
    run_state: str | None = None,
) -> dict[str, Any] | None:
    cur = load_tasklet_run(workspace_root, run_id)
    if not cur:
        return None
    cps = cur.setdefault("checkpoints", [])
    if not isinstance(cps, list):
        cps = []
        cur["checkpoints"] = cps
    seq = len(cps)
    row: dict[str, Any] = {
        "seq": seq,
        "ts": _now(),
        "step": str(step or "").strip(),
        "note": (note or "").strip() or None,
    }
    if run_state:
        row["run_state"] = str(run_state).strip().lower()
    cps.append(row)
    write_tasklet_run(workspace_root, cur)
    return row
