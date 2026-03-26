"""Resolve expected GitHub login for this workspace (registry, .lenses-repo, gh)."""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any


def resolve_expected_github_login(
    workspace_root: Path, registry: dict[str, Any]
) -> str | None:
    gl = registry.get("github_login")
    if isinstance(gl, str) and gl.strip():
        return gl.strip()

    repo_dir = workspace_root / ".lenses-repo"
    if repo_dir.is_dir():
        subs = sorted(
            p.name
            for p in repo_dir.iterdir()
            if p.is_dir() and not p.name.startswith(".")
        )
        if len(subs) == 1:
            return subs[0]

    try:
        r = subprocess.run(
            ["gh", "api", "user", "-q", ".login"],
            cwd=str(workspace_root),
            capture_output=True,
            text=True,
            timeout=15,
        )
        if r.returncode == 0 and r.stdout.strip():
            return r.stdout.strip()
    except (OSError, subprocess.TimeoutExpired):
        pass
    return None
