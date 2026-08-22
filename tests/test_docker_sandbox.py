"""Docker sandbox argv, apply-on-host invariant, and resume API."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from lenses.docs_health import isolation
from lenses.docs_health.api_handlers import post_project_docs_health
from lenses.docs_health import store
from lenses.sandbox.docker_runner import (
    build_docs_health_docker_argv,
    sandbox_cidfile_path,
    tasklet_checkpoint_dir,
)


def test_build_docker_argv_mounts_repo_ro_and_checkpoint_rw(tmp_path: Path) -> None:
    ws = tmp_path / "ws"
    ws.mkdir()
    slug = "demo"
    proj = ws / slug
    proj.mkdir()
    (ws / "lenses").mkdir()
    cid = sandbox_cidfile_path(ws, "sess123")
    argv = build_docs_health_docker_argv(
        workspace_root=ws,
        repo_root=proj,
        lenses_repo_root=ws / "lenses",
        project_slug=slug,
        session_id="sess123",
        tasklet_run_id="tr456",
        step="enrich",
        cidfile=cid,
    )
    joined = " ".join(argv)
    assert "/repo:ro" in joined
    assert "/workspace:rw" in joined
    assert "/checkpoint:rw" in joined
    assert "--cidfile" in argv
    assert argv[-1] == "/repo"


def test_tasklet_checkpoint_dir_is_stable(tmp_path: Path) -> None:
    ws = tmp_path / "ws"
    ws.mkdir()
    a = tasklet_checkpoint_dir(ws, "abc123")
    b = tasklet_checkpoint_dir(ws, "abc123")
    assert a == b
    assert a.is_dir()


def test_apply_step_runs_inline_even_when_backend_is_docker(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Apply must not use Docker or subprocess workers (host repo write policy)."""
    calls: list[str] = []

    def fake_execute(ws: Path, child: Path, slug: str, sess: dict[str, Any], step: str, bundle: dict[str, Any]):
        calls.append(step)
        return 200, {"ok": True, "session": sess}

    monkeypatch.setattr(isolation, "execute_docs_health_session_step", fake_execute)
    monkeypatch.setenv("LENSES_DOCS_HEALTH_STEP_BACKEND", "docker")
    ws = tmp_path / "ws"
    ws.mkdir()
    child = ws / "p"
    child.mkdir()
    sess = {"id": "s1", "events": []}
    code, body = isolation.run_docs_health_session_step(
        ws,
        child,
        "p",
        sess,
        "apply",
        {"can_write_project": True},
    )
    assert code == 200
    assert calls == ["apply"]


def test_session_resume_after_cancel(tmp_path: Path) -> None:
    ws = tmp_path / "ws"
    ws.mkdir()
    slug = "demo"
    proj = ws / slug
    proj.mkdir()
    (proj / ".git").mkdir()
    store.ensure_store_dir(ws, slug)
    run_id = "runtest0001"
    cluster_id = "cluster-1"
    store.write_run(
        ws,
        slug,
        {
            "id": run_id,
            "project": slug,
            "findings": [{"id": "f1", "title": "Gap"}],
            "clusters": [{"id": cluster_id, "label": "Minor · diagram", "finding_ids": ["f1"]}],
            "score": {"value": 50},
        },
    )
    registry: dict[str, Any] = {}
    bundle = {"can_read_project": True, "can_write_project": True}
    cap: list[tuple[int, dict[str, Any]]] = []

    def send_json(code: int, body: dict[str, Any]) -> None:
        cap.append((code, body))

    post_project_docs_health(
        ws,
        registry,
        slug,
        {"op": "create_session", "cluster_id": cluster_id, "run_id": run_id},
        bundle=bundle,
        send_json=send_json,
    )
    sid = str(cap[-1][1]["session"]["id"])
    post_project_docs_health(
        ws,
        registry,
        slug,
        {"op": "session_cancel", "session_id": sid},
        bundle=bundle,
        send_json=send_json,
    )
    post_project_docs_health(
        ws,
        registry,
        slug,
        {"op": "session_resume", "session_id": sid},
        bundle=bundle,
        send_json=send_json,
    )
    assert cap[-1][0] == 200
    sess = cap[-1][1].get("session") or {}
    assert sess.get("status") == "running"
    assert (sess.get("tasklet_run") or {}).get("state") == "running"
