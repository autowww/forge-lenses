"""Tasklet run + sandbox flags for Docs Health sessions."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from lenses.docs_health.api_handlers import post_project_docs_health
from lenses.docs_health import store
from lenses.tasklet.store import load_tasklet_run


def test_create_session_registers_tasklet_run(tmp_path: Path) -> None:
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
    captured: list[tuple[int, dict[str, Any]]] = []

    def send_json(code: int, body: dict[str, Any]) -> None:
        captured.append((code, body))

    post_project_docs_health(
        ws,
        registry,
        slug,
        {"op": "create_session", "cluster_id": cluster_id, "run_id": run_id},
        bundle=bundle,
        send_json=send_json,
    )
    assert captured[0][0] == 200
    sess = captured[0][1]["session"]
    tr_id = str(sess.get("tasklet_run_id") or "").strip()
    assert len(tr_id) >= 16
    assert sess.get("tasklet", {}).get("id") == "docs_health_remediation"
    assert sess.get("execution", {}).get("resumable") is True
    row = load_tasklet_run(ws, tr_id)
    assert row is not None
    assert row.get("tasklet_id") == "docs_health_remediation"
    assert row.get("docs_health_session_id") == sess.get("id")
    assert row.get("state") == "running"
    assert int(row.get("event_seq") or 0) >= 3
    assert sess.get("run_state") == "running"
    sw = sess.get("scratch_workspace")
    assert isinstance(sw, dict)
    assert sw.get("ok") is True
    assert str(sw.get("worktree_path") or "")


def test_cancel_updates_tasklet_run_status(tmp_path: Path) -> None:
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
    tr_id = str(cap[-1][1]["session"]["tasklet_run_id"])
    post_project_docs_health(
        ws,
        registry,
        slug,
        {"op": "session_cancel", "session_id": sid},
        bundle=bundle,
        send_json=send_json,
    )
    row = load_tasklet_run(ws, tr_id)
    assert row is not None
    assert row.get("state") == "stopped"
    assert str(row.get("stop_reason") or "").lower() == "cancelled"
