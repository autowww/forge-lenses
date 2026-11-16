"""Read git user.name / user.email from a repo checkout (for UI labels)."""

from __future__ import annotations

import subprocess
from pathlib import Path


def git_user_identity(repo: Path) -> tuple[str, str]:
    """
    Return (user.name, user.email) from `git config` in repo, or ("", "") if unavailable.
    """
    name = _git_config(repo, "user.name")
    email = _git_config(repo, "user.email")
    return name, email


def _git_config(repo: Path, key: str) -> str:
    try:
        r = subprocess.run(
            ["git", "-C", str(repo), "config", key],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if r.returncode != 0:
            return ""
        return (r.stdout or "").strip()
    except (OSError, subprocess.TimeoutExpired):
        return ""
