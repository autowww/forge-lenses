"""
Docker-backed sandbox runner for tasklets (Docs Health steps).

Uses ``docker run --cidfile`` so :func:`lenses.sandbox.active.stop_session_execution` can
``docker kill`` the running container. Checkpoint and heartbeat data live under
``.lenses-local/tasklet-runs/<id>.sandbox/`` on the host (mounted ``/checkpoint`` in the container).

Apply steps must not run inside Docker — callers should execute them on the host only.
"""

from __future__ import annotations

import json
import os
import subprocess
import threading
import time
from pathlib import Path
from typing import Any, Callable

from lenses.docs_health import store as dh_store
from lenses.sandbox.active import register_docker_container
from lenses.tasklet import store as tr_store

# --- Paths ---------------------------------------------------------------------------

def _safe_id(s: str) -> str:
    x = str(s or "").strip().replace(os.sep, "_").replace("/", "_")
    if not x or ".." in x:
        raise ValueError("invalid_id")
    return x


def tasklet_checkpoint_dir(workspace_root: Path, tasklet_run_id: str) -> Path:
    """Persistent volume for sandbox heartbeats and auxiliary checkpoint files."""
    sid = _safe_id(tasklet_run_id)
    d = workspace_root.resolve() / ".lenses-local" / "tasklet-runs" / f"{sid}.sandbox"
    d.mkdir(parents=True, exist_ok=True)
    try:
        os.chmod(d, 0o700)
    except OSError:
        pass
    return d


def sandbox_cidfile_dir(workspace_root: Path) -> Path:
    d = workspace_root.resolve() / ".lenses-local" / "sandbox-cids"
    d.mkdir(parents=True, exist_ok=True)
    try:
        os.chmod(d, 0o700)
    except OSError:
        pass
    return d


def sandbox_cidfile_path(workspace_root: Path, session_id: str) -> Path:
    return sandbox_cidfile_dir(workspace_root) / f"{_safe_id(session_id)}.cid"


# --- Docker CLI helpers --------------------------------------------------------------

def docker_inspect_status(container_id: str) -> str | None:
    """Return Docker status string (e.g. ``running``, ``exited``) or None."""
    cid = str(container_id or "").strip()
    if not cid:
        return None
    try:
        r = subprocess.run(
            ["docker", "inspect", "-f", "{{.State.Status}}", cid],
            capture_output=True,
            text=True,
            timeout=30,
        )
        if r.returncode != 0:
            return None
        return (r.stdout or "").strip() or None
    except (OSError, subprocess.TimeoutExpired):
        return None


def docker_stop(container_id: str, *, timeout_s: int = 30) -> bool:
    cid = str(container_id or "").strip()
    if not cid:
        return False
    try:
        r = subprocess.run(
            ["docker", "stop", "-t", str(int(timeout_s)), cid],
            capture_output=True,
            text=True,
            timeout=timeout_s + 15,
        )
        return r.returncode == 0
    except (OSError, subprocess.TimeoutExpired):
        return False


def docker_kill(container_id: str) -> bool:
    cid = str(container_id or "").strip()
    if not cid:
        return False
    try:
        r = subprocess.run(["docker", "kill", cid], capture_output=True, text=True, timeout=30)
        return r.returncode == 0
    except (OSError, subprocess.TimeoutExpired):
        return False


def cleanup_cidfile(path: Path) -> None:
    try:
        path.unlink()
    except FileNotFoundError:
        pass
    except OSError:
        pass


# --- argv builder --------------------------------------------------------------------


def build_docs_health_docker_argv(
    *,
    workspace_root: Path,
    repo_root: Path,
    lenses_repo_root: Path,
    project_slug: str,
    session_id: str,
    tasklet_run_id: str,
    step: str,
    cidfile: Path,
) -> list[str]:
    """
    ``docker run`` for one Docs Health step.

    Mounts:
    - Workspace read-write at ``/workspace`` (``.lenses-local`` store + scratch live here).
    - Project checkout **read-only** at ``/repo`` (draft/verify must not mutate the live tree from the sandbox).
    - Lenses sources read-only at ``/lenses-src``.
    - Tasklet checkpoint dir read-write at ``/checkpoint``.
    """
    wr = workspace_root.resolve()
    rr = repo_root.resolve()
    lr = lenses_repo_root.resolve()
    ck = tasklet_checkpoint_dir(wr, tasklet_run_id)
    img = str(os.environ.get("LENSES_SANDBOX_IMAGE") or "python:3.12-slim")
    step_lc = str(step or "").strip().lower()
    cidfile.parent.mkdir(parents=True, exist_ok=True)
    return [
        "docker",
        "run",
        "--rm",
        "-i",
        "--cidfile",
        str(cidfile.resolve()),
        "-v",
        f"{wr}:/workspace:rw",
        "-v",
        f"{rr}:/repo:ro",
        "-v",
        f"{lr}:/lenses-src:ro",
        "-v",
        f"{ck.resolve()}:/checkpoint:rw",
        "-w",
        "/lenses-src",
        "-e",
        "PYTHONPATH=/lenses-src",
        "-e",
        "LENSES_CHECKPOINT_ROOT=/checkpoint",
        img,
        "python",
        "-m",
        "lenses.docs_health.step_cli",
        "--workspace-root",
        "/workspace",
        "--project-slug",
        project_slug,
        "--session-id",
        session_id,
        "--step",
        step_lc,
        "--repo-root",
        "/repo",
    ]


def poll_cidfile_and_register(
    cidfile: Path,
    session_id: str,
    stop_event: threading.Event,
    *,
    timeout_s: float = 60.0,
) -> str | None:
    """Wait until Docker writes the container id, then register for hard stop."""
    deadline = time.monotonic() + timeout_s
    while not stop_event.is_set() and time.monotonic() < deadline:
        try:
            if cidfile.is_file():
                raw = cidfile.read_text(encoding="utf-8").strip()
                if raw:
                    register_docker_container(session_id, raw)
                    return raw
        except OSError:
            pass
        stop_event.wait(0.05)
    return None


def spawn_cidfile_watcher(
    cidfile: Path,
    session_id: str,
    stop_event: threading.Event,
) -> tuple[threading.Thread, Callable[[], None]]:
    """Background thread: register container id as soon as ``--cidfile`` is populated."""

    def run() -> None:
        poll_cidfile_and_register(cidfile, session_id, stop_event)

    t = threading.Thread(target=run, name=f"lenses-cid-{session_id[:8]}", daemon=True)
    t.start()

    def join_watcher() -> None:
        stop_event.set()
        t.join(timeout=2.0)

    return t, join_watcher


def write_host_heartbeat(checkpoint_dir: Path, *, step: str, container_id: str | None, status: str) -> None:
    """Host-side heartbeat after a sandbox step (complements in-container heartbeat)."""
    p = checkpoint_dir / "host_heartbeat.json"
    payload = {
        "ts": dh_store.now_iso(),
        "step": step,
        "container_id": container_id,
        "status": status,
    }
    try:
        p.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
        os.chmod(p, 0o600)
    except OSError:
        pass


def patch_tasklet_sandbox(
    workspace_root: Path,
    tasklet_run_id: str,
    updates: dict[str, Any],
) -> None:
    """Merge ``updates`` into persisted ``sandbox`` on the TaskletRun."""
    tid = str(tasklet_run_id or "").strip()
    if not tid:
        return
    cur = tr_store.load_tasklet_run(Path(workspace_root), tid)
    if not cur:
        return
    sb = dict(cur.get("sandbox") or {}) if isinstance(cur.get("sandbox"), dict) else {}
    sb.update(updates)
    be = sb.get("backend") if isinstance(sb.get("backend"), str) else None
    if be not in ("docker", "fleet", "inline", "process"):
        be = cur.get("sandbox_backend") if isinstance(cur.get("sandbox_backend"), str) else None
    if be not in ("docker", "fleet", "inline", "process"):
        be = "docker"
    tr_store.update_tasklet_run(Path(workspace_root), tid, sandbox=sb, sandbox_backend=be)


def record_sandbox_step_outcome(
    workspace_root: Path,
    tasklet_run_id: str,
    *,
    step: str,
    container_id: str | None,
    docker_status: str | None,
    worker_ok: bool,
    error_tag: str | None = None,
) -> None:
    """Expose lifecycle + failure info on the TaskletRun for Studio."""
    patch_tasklet_sandbox(
        workspace_root,
        tasklet_run_id,
        {
            "last_step": step,
            "container_id": container_id,
            "docker_status": docker_status,
            "last_worker_ok": worker_ok,
            "last_error": error_tag,
            "updated_at": dh_store.now_iso(),
        },
    )
