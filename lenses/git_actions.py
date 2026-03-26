"""Guarded git subprocess actions for the lenses HTTP API."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path
from typing import Any


GIT_ACTION_ARGS: dict[str, list[str]] = {
    "fetch": ["fetch", "origin"],
    "pull": ["pull", "--ff-only"],
    "status": ["status", "-sb"],
}


def _is_loopback_client(host: str) -> bool:
    h = (host or "").strip()
    if h in ("127.0.0.1", "::1", "localhost"):
        return True
    if h.startswith("::ffff:") and h[7:] == "127.0.0.1":
        return True
    return False


def client_may_run_privileged_local_api(client_ip: str) -> bool:
    """Loopback-only unless LENSES_ALLOW_GIT_ACTIONS=1 (git POST, sticker-board save, etc.)."""
    if os.environ.get("LENSES_ALLOW_GIT_ACTIONS", "").strip() in ("1", "true", "yes"):
        return True
    return _is_loopback_client(client_ip)


def client_may_run_git_actions(client_ip: str) -> bool:
    return client_may_run_privileged_local_api(client_ip)


def client_may_write_sticker_board(client_ip: str) -> bool:
    """Same network policy as git actions (loopback or LENSES_ALLOW_GIT_ACTIONS)."""
    return client_may_run_privileged_local_api(client_ip)


def run_git_action(repo: Path, action: str) -> dict[str, Any]:
    args = GIT_ACTION_ARGS.get(action)
    if args is None:
        return {
            "ok": False,
            "error": f"Unknown action: {action}",
            "stdout": "",
            "stderr": "",
            "exit_code": -1,
        }
    try:
        r = subprocess.run(
            ["git", "-C", str(repo), *args],
            capture_output=True,
            text=True,
            timeout=300,
        )
        return {
            "ok": r.returncode == 0,
            "stdout": r.stdout or "",
            "stderr": r.stderr or "",
            "exit_code": r.returncode,
            "error": "",
        }
    except subprocess.TimeoutExpired:
        return {
            "ok": False,
            "error": "Git command timed out",
            "stdout": "",
            "stderr": "",
            "exit_code": -1,
        }
    except OSError as exc:
        return {
            "ok": False,
            "error": str(exc),
            "stdout": "",
            "stderr": "",
            "exit_code": -1,
        }
