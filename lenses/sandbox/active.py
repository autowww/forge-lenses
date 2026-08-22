"""Track in-flight sandbox handles per Docs Health session (SIGKILL / docker kill on cancel)."""

from __future__ import annotations

import subprocess
import threading
from typing import Any

_lock = threading.Lock()
# session_id -> {"popen": Popen|None, "docker_container_id": str|None}
_handles: dict[str, dict[str, Any]] = {}


def register_subprocess(session_id: str, proc: subprocess.Popen[Any]) -> None:
    sid = str(session_id or "").strip()
    if not sid:
        return
    with _lock:
        h = _handles.setdefault(sid, {})
        h["popen"] = proc
        h["docker_container_id"] = h.get("docker_container_id")


def register_docker_container(session_id: str, container_id: str) -> None:
    sid = str(session_id or "").strip()
    cid = str(container_id or "").strip()
    if not sid or not cid:
        return
    with _lock:
        h = _handles.setdefault(sid, {})
        h["docker_container_id"] = cid
        h["popen"] = h.get("popen")


def clear_session_handles(session_id: str) -> None:
    sid = str(session_id or "").strip()
    if not sid:
        return
    with _lock:
        _handles.pop(sid, None)


def stop_session_execution(session_id: str) -> None:
    """Physically stop subprocess and/or Docker container for this session."""
    sid = str(session_id or "").strip()
    if not sid:
        return
    with _lock:
        h = dict(_handles.get(sid) or {})
    proc = h.get("popen")
    if proc is not None:
        try:
            proc.kill()
        except OSError:
            pass
    dc = h.get("docker_container_id")
    if dc:
        try:
            subprocess.run(
                ["docker", "kill", str(dc)],
                capture_output=True,
                text=True,
                timeout=30,
            )
        except (OSError, subprocess.TimeoutExpired):
            pass
    with _lock:
        _handles.pop(sid, None)
