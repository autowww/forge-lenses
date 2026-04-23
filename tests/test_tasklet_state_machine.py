"""TaskletRun state machine and durable event persistence."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from lenses.docs_health.api_handlers import post_project_docs_health
from lenses.docs_health import store
from lenses.docs_health.run_projection import merge_docs_health_session_view
from lenses.tasklet.run_events import load_session_events
from lenses.docs_health.run_sync import resume_docs_health_run
from lenses.tasklet.state_machine import is_terminal, transition_allowed, try_apply_state_transition
from lenses.tasklet.store import create_tasklet_run, load_tasklet_run, tasklet_run_path


def test_transition_rules_terminal_blocks_progress() -> None:
    assert not transition_allowed("completed", "running")
    assert transition_allowed("stopped", "running")
    assert not transition_allowed("failed", "running")
    assert is_terminal("completed")


def test_apply_transition_roundtrip(tmp_path: Path) -> None:
    ws = tmp_path / "w"
    ws.mkdir()
    tr = create_tasklet_run(
        ws,
        tasklet_id="docs_health_remediation",
        tasklet_version=1,
        kind="docs_health_remediation",
        project_slug="p",
    )
    rid = str(tr["id"])
    assert try_apply_state_transition(ws, rid, "preparing")[0] is True
    assert try_apply_state_transition(ws, rid, "running")[0] is True
    assert load_tasklet_run(ws, rid).get("state") == "running"


def test_persisted_run_reloads_after_simulated_restart(tmp_path: Path) -> None:
    """Same as cold reload: new load_tasklet_run from filesystem."""
    ws = tmp_path / "w"
    ws.mkdir()
    tr = create_tasklet_run(
        ws,
        tasklet_id="docs_health_remediation",
        tasklet_version=1,
        kind="docs_health_remediation",
        project_slug="p",
    )
    rid = str(tr["id"])
    try_apply_state_transition(ws, rid, "preparing")
    try_apply_state_transition(ws, rid, "running")
    p = tasklet_run_path(ws, rid)
    assert p.is_file()
    text = p.read_text(encoding="utf-8")
    row2 = load_tasklet_run(ws, rid)
    assert row2 is not None
    assert row2.get("state") == "running"
    # Re-parse JSON as if another process read the file
    import json

    row3 = json.loads(text)
    assert row3.get("state") in ("running", row2.get("state"))


def test_session_get_reconstructs_events_from_jsonl(tmp_path: Path) -> None:
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
    ev = load_session_events(ws, tr_id)
    assert len(ev) >= 3
    merged = merge_docs_health_session_view(ws, slug, sid)
    assert merged is not None
    assert merged.get("run_state") == "running"
    assert isinstance(merged.get("events"), list)
    assert len(merged.get("events") or []) >= 3


def test_cancelled_run_rejects_session_step(tmp_path: Path) -> None:
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
        {"op": "session_step", "session_id": sid, "step": "enrich"},
        bundle=bundle,
        send_json=send_json,
    )
    assert cap[-1][0] == 409
    assert cap[-1][1].get("detail") == "cancelled"


def test_stopped_to_running_resume(tmp_path: Path) -> None:
    ws = tmp_path / "w"
    ws.mkdir()
    tr = create_tasklet_run(
        ws,
        tasklet_id="docs_health_remediation",
        tasklet_version=1,
        kind="docs_health_remediation",
        project_slug="p",
    )
    rid = str(tr["id"])
    try_apply_state_transition(ws, rid, "preparing")
    try_apply_state_transition(ws, rid, "running")
    try_apply_state_transition(ws, rid, "stopping")
    try_apply_state_transition(ws, rid, "stopped", stop_reason="cancelled")
    assert load_tasklet_run(ws, rid).get("state") == "stopped"
    ok, err = resume_docs_health_run(ws, rid)
    assert ok and err is None
    row = load_tasklet_run(ws, rid)
    assert row.get("state") == "running"
    assert row.get("stop_reason") is None
