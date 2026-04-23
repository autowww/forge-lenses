"""
Run-scoped scratch workspace: git worktree under ``.lenses-local`` only.

No drafting step writes to the source checkout; materialization targets the worktree root.
"""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
from pathlib import Path
from typing import Any

from lenses.docs_health import store


def scratch_dir(workspace_root: Path, project_slug: str, session_id: str) -> Path:
    sid = str(session_id or "").strip().replace(os.sep, "_").replace("/", "_")
    if not sid or ".." in sid:
        raise ValueError("invalid_session_id")
    return store.ensure_store_dir(workspace_root, project_slug) / "scratch" / sid


def worktree_path(workspace_root: Path, project_slug: str, session_id: str) -> Path:
    return scratch_dir(workspace_root, project_slug, session_id) / "wt"


def scratch_meta_path(workspace_root: Path, project_slug: str, session_id: str) -> Path:
    return scratch_dir(workspace_root, project_slug, session_id) / "scratch_meta.json"


def _git_ok(repo_root: Path) -> bool:
    rr = repo_root.resolve()
    return (rr / ".git").is_dir() and (rr / ".git").exists()


def ensure_run_scratch_workspace(
    repo_root: Path,
    workspace_root: Path,
    project_slug: str,
    session_id: str,
) -> dict[str, Any]:
    """
    Create or reuse a detached worktree for this session/run.

    Returns ``worktree_path`` when successful; on failure (no git / worktree error), returns
    ``ok: False`` so callers can still use artifact-only drafting without touching source.
    """
    rr = repo_root.resolve()
    sid = str(session_id or "").strip()
    if not sid:
        return {"ok": False, "error": "missing_session_id"}
    base = scratch_dir(workspace_root, project_slug, session_id)
    base.mkdir(parents=True, exist_ok=True)
    wt = base / "wt"
    meta_p = scratch_meta_path(workspace_root, project_slug, session_id)

    if wt.is_dir() and (wt / ".git").exists():
        if not meta_p.is_file():
            meta_p.write_text(
                json.dumps(
                    {"session_id": sid, "reused": True, "updated_at": store.now_iso()},
                    indent=2,
                    sort_keys=True,
                ),
                encoding="utf-8",
            )
        return {
            "ok": True,
            "worktree_path": str(wt.resolve()),
            "reused": True,
            "source": "existing_worktree",
        }

    draft_fallback = base / "draft_root"
    if draft_fallback.is_dir():
        return {
            "ok": True,
            "worktree_path": str(draft_fallback.resolve()),
            "reused": True,
            "source": "existing_draft_root",
        }

    if not _git_ok(rr):
        draft_fallback.mkdir(parents=True, exist_ok=True)
        meta_p.write_text(
            json.dumps(
                {
                    "session_id": sid,
                    "created_at": store.now_iso(),
                    "worktree_path": str(draft_fallback.resolve()),
                    "mode": "isolated_dir",
                },
                indent=2,
                sort_keys=True,
            ),
            encoding="utf-8",
        )
        return {
            "ok": True,
            "worktree_path": str(draft_fallback.resolve()),
            "reused": False,
            "source": "isolated_dir",
        }

    try:
        r = subprocess.run(
            ["git", "-C", str(rr), "worktree", "add", "--detach", str(wt), "HEAD"],
            capture_output=True,
            text=True,
            timeout=120,
        )
        if r.returncode != 0:
            draft_fallback.mkdir(parents=True, exist_ok=True)
            meta_p.write_text(
                json.dumps(
                    {
                        "session_id": sid,
                        "created_at": store.now_iso(),
                        "worktree_path": str(draft_fallback.resolve()),
                        "mode": "isolated_dir",
                        "fallback_from": "git_worktree_add_failed",
                    },
                    indent=2,
                    sort_keys=True,
                ),
                encoding="utf-8",
            )
            return {
                "ok": True,
                "worktree_path": str(draft_fallback.resolve()),
                "reused": False,
                "source": "isolated_dir",
                "detail": (r.stderr or r.stdout or "").strip()[:500],
            }
    except (OSError, subprocess.TimeoutExpired) as e:
        draft_fallback.mkdir(parents=True, exist_ok=True)
        meta_p.write_text(
            json.dumps(
                {
                    "session_id": sid,
                    "created_at": store.now_iso(),
                    "worktree_path": str(draft_fallback.resolve()),
                    "mode": "isolated_dir",
                    "fallback_from": "worktree_exception",
                    "detail": str(e)[:500],
                },
                indent=2,
                sort_keys=True,
            ),
            encoding="utf-8",
        )
        return {
            "ok": True,
            "worktree_path": str(draft_fallback.resolve()),
            "reused": False,
            "source": "isolated_dir",
        }

    meta_p.write_text(
        json.dumps(
            {
                "session_id": sid,
                "created_at": store.now_iso(),
                "worktree_path": str(wt.resolve()),
            },
            indent=2,
            sort_keys=True,
        ),
        encoding="utf-8",
    )
    try:
        os.chmod(meta_p, 0o600)
    except OSError:
        pass
    return {"ok": True, "worktree_path": str(wt.resolve()), "reused": False, "source": "created"}


def write_patch_to_scratch(
    scratch_root: Path,
    patch: dict[str, str],
) -> dict[str, Any]:
    """Write ``patch`` content under ``scratch_root`` only (isolated tree)."""
    rel = str(patch.get("path") or "").strip()
    content = str(patch.get("content") if patch.get("content") is not None else "")
    if ".." in rel or rel.startswith("/") or not rel.endswith(".md"):
        return {"ok": False, "error": "invalid_patch_path"}
    sr = scratch_root.resolve()
    target = (sr / rel).resolve()
    try:
        target.relative_to(sr)
    except ValueError:
        return {"ok": False, "error": "path_escape"}
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")
    sha = hashlib.sha256(content.encode("utf-8")).hexdigest()
    return {"ok": True, "rel_path": rel, "sha256": sha, "bytes": len(content.encode("utf-8"))}


def discard_run_scratch(
    repo_root: Path,
    workspace_root: Path,
    project_slug: str,
    session_id: str,
) -> dict[str, Any]:
    """Remove worktree and session scratch dir (best-effort). Source repo unchanged."""
    rr = repo_root.resolve()
    sid = str(session_id or "").strip()
    if not sid:
        return {"ok": False, "error": "missing_session_id"}
    wt = worktree_path(workspace_root, project_slug, session_id)
    if wt.is_dir():
        if _git_ok(rr):
            try:
                r = subprocess.run(
                    ["git", "-C", str(rr), "worktree", "remove", "--force", str(wt)],
                    capture_output=True,
                    text=True,
                    timeout=120,
                )
                if r.returncode != 0:
                    return {
                        "ok": False,
                        "error": "git_worktree_remove_failed",
                        "detail": (r.stderr or r.stdout or "").strip()[:2000],
                    }
            except (OSError, subprocess.TimeoutExpired) as e:
                return {"ok": False, "error": "worktree_remove_error", "detail": str(e)[:2000]}
        else:
            # No usable git — remove directory tree only
            import shutil

            try:
                shutil.rmtree(wt, ignore_errors=True)
            except OSError:
                pass
    base = scratch_dir(workspace_root, project_slug, session_id)
    if base.is_dir():
        import shutil

        try:
            shutil.rmtree(base, ignore_errors=True)
        except OSError:
            pass
    return {"ok": True, "discarded": True}
