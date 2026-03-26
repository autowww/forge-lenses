"""Allowlisted subprocess actions for workspace sites (no shell)."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path
from typing import Any


def _is_loopback_client(host: str) -> bool:
    h = (host or "").strip()
    if h in ("127.0.0.1", "::1", "localhost"):
        return True
    if h.startswith("::ffff:") and h[7:] == "127.0.0.1":
        return True
    return False


def client_may_run_shell_actions(client_ip: str) -> bool:
    if os.environ.get("LENSES_ALLOW_ACTIONS", "").strip() in ("1", "true", "yes"):
        return True
    return _is_loopback_client(client_ip)


def _argv_ok(argv: list[str]) -> bool:
    if not argv or not all(isinstance(x, str) and x for x in argv):
        return False
    for a in argv:
        if "\x00" in a:
            return False
    return True


def run_allowlisted_action(
    workspace_root: Path,
    cwd_relative: str,
    argv: list[str],
    *,
    timeout_sec: int = 900,
) -> dict[str, Any]:
    wr = workspace_root.resolve()
    rel = (cwd_relative or ".").strip().replace("\\", "/").strip("/")
    if ".." in rel.split("/"):
        return {
            "ok": False,
            "error": "invalid_cwd_relative",
            "stdout": "",
            "stderr": "",
            "exit_code": -1,
        }
    cwd = (wr / rel).resolve() if rel else wr
    try:
        cwd.relative_to(wr)
    except ValueError:
        return {
            "ok": False,
            "error": "cwd_outside_workspace",
            "stdout": "",
            "stderr": "",
            "exit_code": -1,
        }
    if not cwd.is_dir():
        return {
            "ok": False,
            "error": "cwd_not_a_directory",
            "stdout": "",
            "stderr": "",
            "exit_code": -1,
        }
    if not _argv_ok(argv):
        return {
            "ok": False,
            "error": "invalid_argv",
            "stdout": "",
            "stderr": "",
            "exit_code": -1,
        }
    try:
        r = subprocess.run(
            argv,
            cwd=str(cwd),
            capture_output=True,
            text=True,
            timeout=timeout_sec,
        )
        return {
            "ok": r.returncode == 0,
            "stdout": (r.stdout or "")[-120_000:],
            "stderr": (r.stderr or "")[-120_000:],
            "exit_code": r.returncode,
            "error": "",
        }
    except subprocess.TimeoutExpired:
        return {
            "ok": False,
            "error": "timeout",
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
