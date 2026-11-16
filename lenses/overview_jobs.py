"""Async overview chart telemetry jobs — bounded parallelism + file cache."""

from __future__ import annotations

import json
import os
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

from lenses.chart_payloads import build_overview_chart_payload, horizon_query_days, normalized_horizon_id

_DEFAULT_OVERVIEW_CACHE_SEC = 300.0
_MAX_WORKERS = 3

_executor = ThreadPoolExecutor(max_workers=_MAX_WORKERS, thread_name_prefix="lenses-overview")
_registry_lock = threading.Lock()
_jobs: dict[str, dict[str, Any]] = {}
_active_by_cache_key: dict[str, str] = {}


def overview_async_enabled() -> bool:
    raw = os.environ.get("LENSES_OVERVIEW_ASYNC", "1").strip().lower()
    return raw not in ("0", "false", "no", "off")


def overview_cache_ttl_sec() -> float | None:
    raw = os.environ.get("LENSES_OVERVIEW_CACHE_SEC", "").strip()
    if raw == "":
        return _DEFAULT_OVERVIEW_CACHE_SEC
    try:
        v = float(raw)
    except ValueError:
        return _DEFAULT_OVERVIEW_CACHE_SEC
    if v <= 0:
        return None
    return v


def _cache_file(workspace_root: Path) -> Path:
    return workspace_root / ".lenses-local" / "overview-cache.json"


def _cache_key(horizon_id: str) -> str:
    return normalized_horizon_id(horizon_id)


def _read_cache_file(workspace_root: Path) -> dict[str, Any]:
    path = _cache_file(workspace_root)
    if not path.is_file():
        return {"version": 1, "entries": {}}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(data, dict) and isinstance(data.get("entries"), dict):
            return data
    except (OSError, json.JSONDecodeError, TypeError):
        pass
    return {"version": 1, "entries": {}}


def _write_cache_file(workspace_root: Path, data: dict[str, Any]) -> None:
    path = _cache_file(workspace_root)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, indent=2), encoding="utf-8")
    tmp.replace(path)


def get_stale_overview(
    workspace_root: Path,
    *,
    horizon_id: str,
) -> dict[str, Any] | None:
    """Last-good cached payload regardless of TTL (for 202 pending responses)."""
    hid = _cache_key(horizon_id)
    data = _read_cache_file(workspace_root)
    entry = data.get("entries", {}).get(hid)
    if not isinstance(entry, dict):
        return None
    payload = entry.get("payload")
    return payload if isinstance(payload, dict) else None


def get_cached_overview(
    workspace_root: Path,
    *,
    horizon_id: str,
) -> dict[str, Any] | None:
    """Return cached payload if within TTL, else None."""
    ttl = overview_cache_ttl_sec()
    if ttl is None:
        return None
    hid = _cache_key(horizon_id)
    data = _read_cache_file(workspace_root)
    entry = data.get("entries", {}).get(hid)
    if not isinstance(entry, dict):
        return None
    payload = entry.get("payload")
    if not isinstance(payload, dict):
        return None
    resolved_at = entry.get("resolved_at")
    if not isinstance(resolved_at, (int, float)):
        return None
    if time.time() - float(resolved_at) > ttl:
        return None
    return payload


def store_cached_overview(
    workspace_root: Path,
    *,
    horizon_id: str,
    payload: dict[str, Any],
) -> None:
    hid = _cache_key(horizon_id)
    data = _read_cache_file(workspace_root)
    entries = data.setdefault("entries", {})
    if not isinstance(entries, dict):
        entries = {}
        data["entries"] = entries
    entries[hid] = {
        "horizon": hid,
        "resolved_at": time.time(),
        "payload": payload,
    }
    _write_cache_file(workspace_root, data)


def _job_snapshot(job: dict[str, Any]) -> dict[str, Any]:
    prog = job.get("progress") or {}
    out: dict[str, Any] = {
        "job_id": job.get("job_id"),
        "status": job.get("status"),
        "horizon": job.get("horizon"),
        "cache_hit": bool(job.get("cache_hit")),
        "progress": {
            "done": int(prog.get("done") or 0),
            "total": int(prog.get("total") or 0),
            "phase": str(prog.get("phase") or ""),
            "detail": str(prog.get("detail") or ""),
        },
        "started_at": job.get("started_at"),
        "finished_at": job.get("finished_at"),
        "elapsed_sec": None,
    }
    started = job.get("started_at")
    finished = job.get("finished_at")
    if isinstance(started, (int, float)):
        end = finished if isinstance(finished, (int, float)) else time.time()
        out["elapsed_sec"] = round(float(end) - float(started), 2)
    if job.get("status") == "done" and isinstance(job.get("result"), dict):
        out["result"] = job["result"]
    if job.get("status") == "error":
        out["error"] = str(job.get("error") or "overview_job_failed")
    return out


def get_overview_job(job_id: str) -> dict[str, Any] | None:
    with _registry_lock:
        job = _jobs.get(job_id)
        if job is None:
            return None
        return _job_snapshot(job)


def _set_progress(job_id: str, *, done: int, total: int, phase: str, detail: str = "") -> None:
    with _registry_lock:
        job = _jobs.get(job_id)
        if job is None:
            return
        job["progress"] = {
            "done": max(0, int(done)),
            "total": max(0, int(total)),
            "phase": phase,
            "detail": detail,
        }


def _run_overview_job(
    job_id: str,
    workspace_root: Path,
    state: dict[str, Any],
    *,
    horizon_id: str,
    days: int,
) -> None:
    children = [c for c in (state.get("children") or []) if isinstance(c, dict)]
    total = max(1, len(children))

    def on_progress(patch: dict[str, Any]) -> None:
        _set_progress(
            job_id,
            done=int(patch.get("done") or 0),
            total=int(patch.get("total") or total),
            phase=str(patch.get("phase") or "running"),
            detail=str(patch.get("detail") or ""),
        )

    with _registry_lock:
        job = _jobs.get(job_id)
        if job is None:
            return
        job["status"] = "running"
        job["started_at"] = time.time()
        job["progress"] = {"done": 0, "total": total, "phase": "queued", "detail": ""}

    try:
        payload = build_overview_chart_payload(
            state,
            days=days,
            horizon_id=horizon_id,
            on_progress=on_progress,
        )
        store_cached_overview(workspace_root, horizon_id=horizon_id, payload=payload)
        with _registry_lock:
            job = _jobs.get(job_id)
            if job is None:
                return
            job["status"] = "done"
            job["result"] = payload
            job["finished_at"] = time.time()
            job["progress"] = {
                "done": total,
                "total": total,
                "phase": "done",
                "detail": "complete",
            }
            ck = job.get("cache_key")
            if isinstance(ck, str) and _active_by_cache_key.get(ck) == job_id:
                del _active_by_cache_key[ck]
    except Exception as exc:  # noqa: BLE001 — surface to client poll
        with _registry_lock:
            job = _jobs.get(job_id)
            if job is None:
                return
            job["status"] = "error"
            job["error"] = str(exc)
            job["finished_at"] = time.time()
            ck = job.get("cache_key")
            if isinstance(ck, str) and _active_by_cache_key.get(ck) == job_id:
                del _active_by_cache_key[ck]


def start_overview_job(
    workspace_root: Path,
    state: dict[str, Any],
    *,
    horizon: str | None = None,
    force: bool = False,
) -> dict[str, Any]:
    """Start or attach to an overview compute job. Returns job snapshot."""
    hid = normalized_horizon_id(horizon)
    days = horizon_query_days(horizon)
    ck = f"{workspace_root.resolve()}::{hid}"

    if not force:
        cached = get_cached_overview(workspace_root, horizon_id=hid)
        if cached is not None:
            job_id = str(uuid.uuid4())
            now = time.time()
            snap = {
                "job_id": job_id,
                "status": "done",
                "horizon": hid,
                "cache_hit": True,
                "progress": {"done": 1, "total": 1, "phase": "cache", "detail": "cache hit"},
                "started_at": now,
                "finished_at": now,
                "result": cached,
            }
            with _registry_lock:
                _jobs[job_id] = snap
            return _job_snapshot(snap)

    with _registry_lock:
        existing_id = _active_by_cache_key.get(ck)
        if existing_id:
            existing = _jobs.get(existing_id)
            if existing and existing.get("status") in ("queued", "running"):
                return _job_snapshot(existing)

        job_id = str(uuid.uuid4())
        job = {
            "job_id": job_id,
            "status": "queued",
            "horizon": hid,
            "cache_hit": False,
            "cache_key": ck,
            "progress": {"done": 0, "total": max(1, len(state.get("children") or [])), "phase": "queued", "detail": ""},
            "started_at": None,
            "finished_at": None,
            "result": None,
            "error": None,
        }
        _jobs[job_id] = job
        _active_by_cache_key[ck] = job_id

    _executor.submit(_run_overview_job, job_id, workspace_root, state, horizon_id=hid, days=days)
    with _registry_lock:
        return _job_snapshot(_jobs[job_id])


def max_overview_workers() -> int:
    return _MAX_WORKERS
