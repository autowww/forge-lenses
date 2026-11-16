"""Scratch worktree / isolated draft root and patch artifact boundary for Docs Health."""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any

from lenses.docs_health import store
from lenses.docs_health.artifacts import (
    load_apply_gate,
    load_patch_for_apply,
    session_artifacts_dir,
)
from lenses.docs_health.isolation import run_docs_health_session_step
from lenses.docs_health.scratch_workspace import (
    discard_run_scratch,
    ensure_run_scratch_workspace,
    scratch_dir,
    write_patch_to_scratch,
)
from lenses.docs_health.session_steps import _stage_proposed_patch


def _git_init_with_md(repo: Path) -> None:
    subprocess.run(["git", "init"], cwd=repo, check=True, capture_output=True)
    subprocess.run(
        ["git", "config", "user.email", "t@example.com"],
        cwd=repo,
        check=True,
        capture_output=True,
    )
    subprocess.run(["git", "config", "user.name", "t"], cwd=repo, check=True, capture_output=True)
    (repo / "docs").mkdir(parents=True, exist_ok=True)
    (repo / "docs" / "a.md").write_text("# Old\n", encoding="utf-8")
    subprocess.run(["git", "add", "."], cwd=repo, check=True, capture_output=True)
    subprocess.run(["git", "commit", "-m", "init"], cwd=repo, check=True, capture_output=True)


def test_ensure_scratch_reuses_worktree(tmp_path: Path) -> None:
    ws = tmp_path / "ws"
    slug = "demo"
    proj = ws / slug
    proj.mkdir(parents=True)
    _git_init_with_md(proj)
    store.ensure_store_dir(ws, slug)
    sid = "session-aa"
    a = ensure_run_scratch_workspace(proj, ws, slug, sid)
    b = ensure_run_scratch_workspace(proj, ws, slug, sid)
    assert a.get("ok") and b.get("ok")
    assert Path(str(a["worktree_path"])) == Path(str(b["worktree_path"]))
    assert b.get("reused") is True


def test_write_patch_to_scratch_leaves_source_unchanged(tmp_path: Path) -> None:
    ws = tmp_path / "ws"
    slug = "demo"
    proj = ws / slug
    proj.mkdir(parents=True)
    _git_init_with_md(proj)
    store.ensure_store_dir(ws, slug)
    sid = "session-bb"
    sw = ensure_run_scratch_workspace(proj, ws, slug, sid)
    sr = Path(str(sw["worktree_path"]))
    patch = {"path": "docs/a.md", "content": "# New\n"}
    wr = write_patch_to_scratch(sr, patch)
    assert wr.get("ok") is True
    assert (proj / "docs" / "a.md").read_text(encoding="utf-8") == "# Old\n"
    assert (sr / "docs" / "a.md").read_text(encoding="utf-8") == "# New\n"


def test_stage_proposed_patch_creates_apply_artifact_and_gate(tmp_path: Path) -> None:
    ws = tmp_path / "ws"
    slug = "demo"
    proj = ws / slug
    proj.mkdir(parents=True)
    _git_init_with_md(proj)
    store.ensure_store_dir(ws, slug)
    sid = "session-cc"
    sess: dict[str, Any] = {"id": sid}
    patch = {"path": "docs/a.md", "content": "# Staged\n"}
    out = _stage_proposed_patch(ws, slug, sess, patch, kind="markdown", child=proj)
    assert out["precheck"]["ok"] is True
    assert out["scratch_write"].get("ok") is True
    assert (proj / "docs" / "a.md").read_text(encoding="utf-8") == "# Old\n"
    gate = load_apply_gate(ws, slug, sid)
    assert gate is not None
    assert gate.get("status") == "pending_apply"
    loaded = load_patch_for_apply(ws, slug, sid)
    assert loaded and loaded.get("content") == "# Staged\n"
    art = session_artifacts_dir(ws, slug, sid)
    assert (art / "diff_preview.patch").is_file()
    assert (art / "proposed_patch.json").is_file()


def test_apply_step_writes_repo_from_artifact_only(tmp_path: Path) -> None:
    ws = tmp_path / "ws"
    slug = "demo"
    proj = ws / slug
    proj.mkdir(parents=True)
    _git_init_with_md(proj)
    store.ensure_store_dir(ws, slug)
    sid = "session-dd"
    sess: dict[str, Any] = {"id": sid, "events": []}
    patch = {"path": "docs/a.md", "content": "# From apply\n"}
    _stage_proposed_patch(ws, slug, sess, patch, kind="markdown", child=proj)
    assert (proj / "docs" / "a.md").read_text(encoding="utf-8") == "# Old\n"
    bundle = {"can_write_project": True}
    code, body = run_docs_health_session_step(ws, proj, slug, sess, "apply", bundle)
    assert code == 200
    assert body.get("ok") is True
    assert (proj / "docs" / "a.md").read_text(encoding="utf-8") == "# From apply\n"
    gate2 = load_apply_gate(ws, slug, sid)
    assert gate2 and gate2.get("status") == "applied"
    code2, body2 = run_docs_health_session_step(ws, proj, slug, sess, "apply", bundle)
    assert code2 == 400
    assert body2.get("error") == "patch_already_applied"


def test_discard_removes_scratch(tmp_path: Path) -> None:
    ws = tmp_path / "ws"
    slug = "demo"
    proj = ws / slug
    proj.mkdir(parents=True)
    _git_init_with_md(proj)
    store.ensure_store_dir(ws, slug)
    sid = "session-ee"
    ensure_run_scratch_workspace(proj, ws, slug, sid)
    base = scratch_dir(ws, slug, sid)
    assert base.is_dir()
    dr = discard_run_scratch(proj, ws, slug, sid)
    assert dr.get("ok") is True
    assert not base.exists()


def test_legacy_apply_without_artifact_files(tmp_path: Path) -> None:
    """Older sessions: no on-disk apply gate — apply may still use session ``proposed_patch``."""
    ws = tmp_path / "ws"
    slug = "demo"
    proj = ws / slug
    proj.mkdir(parents=True)
    _git_init_with_md(proj)
    store.ensure_store_dir(ws, slug)
    sid = "session-ff"
    sess: dict[str, Any] = {
        "id": sid,
        "events": [],
        "proposed_patch": {"path": "docs/a.md", "content": "# Legacy\n"},
    }
    bundle = {"can_write_project": True}
    code, _body = run_docs_health_session_step(ws, proj, slug, sess, "apply", bundle)
    assert code == 200
    assert (proj / "docs" / "a.md").read_text(encoding="utf-8") == "# Legacy\n"
