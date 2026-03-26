"""Allowlisted workspace-root shell scripts for the lenses HTTP API (no shell)."""

from __future__ import annotations

import re
import subprocess
from pathlib import Path
from typing import Any

_SCRIPT_NAME_RE = re.compile(r"^[A-Za-z0-9._-]+\.sh$")
_TAIL = 120_000


def script_name_ok(name: str) -> bool:
    if not name or name != Path(name).name:
        return False
    if ".." in name or "/" in name or "\\" in name:
        return False
    return bool(_SCRIPT_NAME_RE.match(name))


def resolve_toolset_script(workspace_root: Path, name: str) -> Path | None:
    if not script_name_ok(name):
        return None
    wr = workspace_root.resolve()
    candidate = (wr / name).resolve()
    try:
        candidate.relative_to(wr)
    except ValueError:
        return None
    if candidate.name != name:
        return None
    if not candidate.is_file() or candidate.suffix.lower() != ".sh":
        return None
    return candidate


def run_toolset_script(
    workspace_root: Path,
    name: str,
    *,
    timeout_sec: int = 900,
) -> dict[str, Any]:
    script = resolve_toolset_script(workspace_root, name)
    if script is None:
        return {
            "ok": False,
            "error": "script_not_found_or_invalid",
            "stdout": "",
            "stderr": "",
            "exit_code": -1,
        }
    wr = workspace_root.resolve()
    try:
        r = subprocess.run(
            ["/bin/bash", str(script)],
            cwd=str(wr),
            capture_output=True,
            text=True,
            timeout=timeout_sec,
        )
        out = (r.stdout or "")[-_TAIL:]
        err = (r.stderr or "")[-_TAIL:]
        return {
            "ok": r.returncode == 0,
            "stdout": out,
            "stderr": err,
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
