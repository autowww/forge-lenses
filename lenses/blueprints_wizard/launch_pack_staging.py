"""
Temporary on-disk zips for large Cursor Launch Pack downloads (experimental).

Orphaned zips are removed when older than TTL (see ``cleanup_expired_staged_zips``): called after
each ``write_staged_zip``, before each download ``GET``, and on a background interval from
``serve.py`` (see ``LENSES_CURSOR_LAUNCH_STAGING_CLEANUP_INTERVAL_MIN``).
"""

from __future__ import annotations

import os
import re
import secrets
import time
from pathlib import Path

_STAGING_ROOT = "cursor-launch-staging"
_TOKEN_RE = re.compile(r"^[A-Za-z0-9._-]{16,512}$")

# Default age after which staged zips are removed (orphans + abandoned downloads).
_DEFAULT_TTL_SEC = 3600


def _safe_session_segment(session_id: str) -> str:
    return re.sub(r"[^A-Za-z0-9._-]", "_", session_id)[:128]


def staging_root_dir(workspace_root: Path) -> Path:
    return workspace_root.resolve() / ".lenses-local" / "blueprints-wizard" / _STAGING_ROOT


def staging_session_dir(workspace_root: Path, session_id: str) -> Path:
    return staging_root_dir(workspace_root) / _safe_session_segment(session_id)


def _resolve_ttl_sec(override: int | None) -> int:
    """Explicit ``ttl_sec`` (e.g. tests) may be small; env default is clamped to at least 60."""
    if override is not None:
        return max(1, int(override))
    raw = os.environ.get("LENSES_CURSOR_LAUNCH_STAGING_TTL_SEC", "").strip()
    if raw:
        try:
            return max(60, int(raw))
        except ValueError:
            pass
    return _DEFAULT_TTL_SEC


def cleanup_expired_staged_zips(
    workspace_root: Path,
    *,
    ttl_sec: int | None = None,
    now: float | None = None,
) -> int:
    """
    Delete ``*.zip`` under ``cursor-launch-staging/`` older than TTL (by mtime).

    Returns the number of files removed. Empty session subdirs are removed.
    Minimum TTL is 60 seconds (clamped).
    """
    root = staging_root_dir(workspace_root)
    if not root.is_dir():
        return 0
    ttl = _resolve_ttl_sec(ttl_sec)
    t0 = time.time() if now is None else float(now)
    removed = 0
    for session_dir in list(root.iterdir()):
        if not session_dir.is_dir():
            continue
        for p in list(session_dir.glob("*.zip")):
            try:
                mtime = p.stat().st_mtime
            except OSError:
                continue
            if t0 - mtime <= ttl:
                continue
            try:
                p.unlink()
                removed += 1
            except OSError:
                continue
        try:
            next(session_dir.iterdir())
        except StopIteration:
            try:
                session_dir.rmdir()
            except OSError:
                pass
        except OSError:
            pass
    return removed


def validate_download_token(token: str) -> bool:
    return bool(token and _TOKEN_RE.fullmatch(token))


def write_staged_zip(workspace_root: Path, session_id: str, raw: bytes) -> str:
    """Write ``raw`` to a unique file; return opaque token (filename stem)."""
    token = secrets.token_urlsafe(32)
    d = staging_session_dir(workspace_root, session_id)
    d.mkdir(parents=True, exist_ok=True)
    (d / f"{token}.zip").write_bytes(raw)
    cleanup_expired_staged_zips(workspace_root)
    return token


def staged_zip_path(workspace_root: Path, session_id: str, token: str) -> Path | None:
    if not validate_download_token(token):
        return None
    p = staging_session_dir(workspace_root, session_id) / f"{token}.zip"
    if p.is_file():
        try:
            p.resolve().relative_to(staging_session_dir(workspace_root, session_id).resolve())
        except ValueError:
            return None
        return p
    return None


def consume_staged_zip(path: Path) -> None:
    """Delete after successful transfer (ignore errors)."""
    try:
        path.unlink(missing_ok=True)
    except OSError:
        pass
