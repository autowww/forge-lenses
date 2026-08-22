"""Runtime state for virtual camera profiles (ephemeral + persisted hints)."""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

RUNTIME_FILENAME = "virtual-camera-runtime.json"

STATES = frozenset({"stopped", "starting", "running", "stopping", "error"})


def runtime_path(workspace_root: Path) -> Path:
    return workspace_root.resolve() / ".lenses-local" / RUNTIME_FILENAME


def _now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def load_runtime(workspace_root: Path) -> dict[str, Any]:
    p = runtime_path(workspace_root)
    if not p.is_file():
        return {"profiles": {}}
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"profiles": {}}
    if not isinstance(data, dict):
        return {"profiles": {}}
    profiles = data.get("profiles")
    if not isinstance(profiles, dict):
        profiles = {}
    return {"profiles": profiles}


def save_runtime(workspace_root: Path, data: dict[str, Any]) -> None:
    p = runtime_path(workspace_root)
    p.parent.mkdir(parents=True, exist_ok=True)
    try:
        os.chmod(p.parent, 0o700)
    except OSError:
        pass
    tmp = p.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")
    tmp.replace(p)
    try:
        os.chmod(p, 0o600)
    except OSError:
        pass


def get_profile_runtime(workspace_root: Path, profile_id: str) -> dict[str, Any]:
    pid = str(profile_id or "").strip()
    rt = load_runtime(workspace_root)
    profiles = rt.get("profiles") if isinstance(rt.get("profiles"), dict) else {}
    row = profiles.get(pid)
    if not isinstance(row, dict):
        return _default_runtime()
    return _normalize_runtime(row)


def _default_runtime() -> dict[str, Any]:
    return {
        "state": "stopped",
        "pid": None,
        "started_at": None,
        "last_error": None,
        "error_code": None,
        "error_detail": None,
        "stderr_tail": None,
        "source_busy_holder": None,
        "input_device_path": None,
        "output_device_path": None,
    }


def _normalize_runtime(row: dict[str, Any]) -> dict[str, Any]:
    state = str(row.get("state") or "stopped").strip().lower()
    if state not in STATES:
        state = "stopped"
    pid = row.get("pid")
    try:
        pid = int(pid) if pid is not None else None
    except (TypeError, ValueError):
        pid = None
    return {
        "state": state,
        "pid": pid,
        "started_at": row.get("started_at"),
        "last_error": row.get("last_error"),
        "error_code": row.get("error_code"),
        "error_detail": row.get("error_detail"),
        "stderr_tail": row.get("stderr_tail"),
        "source_busy_holder": row.get("source_busy_holder"),
        "input_device_path": row.get("input_device_path"),
        "output_device_path": row.get("output_device_path"),
    }


def set_profile_runtime(workspace_root: Path, profile_id: str, patch: dict[str, Any]) -> dict[str, Any]:
    pid = str(profile_id or "").strip()
    rt = load_runtime(workspace_root)
    profiles = rt.get("profiles") if isinstance(rt.get("profiles"), dict) else {}
    cur = _normalize_runtime(profiles.get(pid) or {})
    merged = {**cur, **{k: v for k, v in patch.items() if v is not None or k in patch}}
    if "state" in patch:
        st = str(patch.get("state") or "stopped").strip().lower()
        merged["state"] = st if st in STATES else "stopped"
    profiles[pid] = merged
    rt["profiles"] = profiles
    save_runtime(workspace_root, rt)
    return merged


def mark_profile_stopped(workspace_root: Path, profile_id: str) -> dict[str, Any]:
    return set_profile_runtime(workspace_root, profile_id, {"state": "stopped", "pid": None})


def clear_profile_runtime(workspace_root: Path, profile_id: str) -> None:
    pid = str(profile_id or "").strip()
    rt = load_runtime(workspace_root)
    profiles = rt.get("profiles") if isinstance(rt.get("profiles"), dict) else {}
    profiles.pop(pid, None)
    rt["profiles"] = profiles
    save_runtime(workspace_root, rt)


def elapsed_seconds(started_at: str | None) -> int | None:
    if not started_at:
        return None
    try:
        dt = datetime.fromisoformat(str(started_at).replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return max(0, int((datetime.now(timezone.utc) - dt).total_seconds()))
    except (TypeError, ValueError):
        return None


def status_payload(workspace_root: Path, profile_id: str, profile: dict[str, Any]) -> dict[str, Any]:
    rt = get_profile_runtime(workspace_root, profile_id)
    return {
        "ok": True,
        "profile_id": profile_id,
        "state": rt["state"],
        "pid": rt["pid"],
        "started_at": rt["started_at"],
        "elapsed_seconds": elapsed_seconds(rt.get("started_at")),
        "last_error": rt.get("last_error"),
        "error_code": rt.get("error_code"),
        "error_detail": rt.get("error_detail"),
        "stderr_tail": rt.get("stderr_tail"),
        "source_busy_holder": rt.get("source_busy_holder"),
        "input_device_path": rt.get("input_device_path"),
        "output_device_path": rt.get("output_device_path"),
        "source": profile.get("source"),
        "virtual": profile.get("virtual"),
        "resolution": profile.get("resolution"),
        "fps": profile.get("fps"),
    }
