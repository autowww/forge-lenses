"""Sprint 6 — tasklet registry, follow-up work rows, and workspace aggregation."""

from __future__ import annotations

from pathlib import Path

from lenses.docs_health import store as dh_store
from lenses.tasklet.catalog import list_tasklet_runs_for_project
from lenses.tasklet.registry import list_builtin_tasklet_definitions, resolve_tasklet
from lenses.tasklet.state_machine import try_apply_state_transition
from lenses.tasklet.store import create_tasklet_run, load_tasklet_run


def test_builtin_tasklet_definition_resolves() -> None:
    spec = resolve_tasklet("docs_health_remediation", 1)
    assert spec and spec.get("kind") == "docs_health_remediation"
    assert spec.get("schema_version") == 1
    assert "executor" in spec
    defs = list_builtin_tasklet_definitions()
    assert any(d.get("id") == "docs_health_remediation" for d in defs)


def test_tasklet_followup_work_items_stopped_run(tmp_path: Path) -> None:
    registry: dict = {"ignore_paths": []}
    tr = create_tasklet_run(
        tmp_path,
        tasklet_id="docs_health_remediation",
        tasklet_version=1,
        kind="docs_health_remediation",
        project_slug="demo-proj",
        docs_health_session_id="sess123",
        agent_runtime_session_id="ar1",
        sandbox_backend="inline",
        metadata={"cluster_id": "c1", "scan_run_id": "r1"},
    )
    rid = str(tr["id"])
    ok, err = try_apply_state_transition(tmp_path, rid, "preparing")
    assert ok, err
    ok, err = try_apply_state_transition(tmp_path, rid, "running")
    assert ok, err
    ok, err = try_apply_state_transition(tmp_path, rid, "stopping")
    assert ok, err
    ok, err = try_apply_state_transition(tmp_path, rid, "stopped", stop_reason="cancelled")
    assert ok, err
    assert load_tasklet_run(tmp_path, rid).get("state") == "stopped"

    items = dh_store.tasklet_followup_work_items(tmp_path, registry, limit=20)
    assert any(i.get("tasklet_run_id") == rid for i in items)
    hit = next(i for i in items if i.get("tasklet_run_id") == rid)
    assert hit.get("kind") == "tasklet_run"
    assert "docs-health/session/sess123" in str(hit.get("docs_health_session_href") or "")


def test_all_open_work_items_merges_tasklet_rows(tmp_path: Path) -> None:
    registry = {"ignore_paths": []}
    tr = create_tasklet_run(
        tmp_path,
        tasklet_id="docs_health_remediation",
        tasklet_version=1,
        kind="docs_health_remediation",
        project_slug="p1",
        docs_health_session_id="s1",
        agent_runtime_session_id="a1",
        sandbox_backend="inline",
    )
    rid = str(tr["id"])
    try_apply_state_transition(tmp_path, rid, "preparing")
    try_apply_state_transition(tmp_path, rid, "running")
    try_apply_state_transition(tmp_path, rid, "awaiting_input")

    merged = dh_store.all_open_work_items(tmp_path, registry, limit=50)
    assert any(str(x.get("id", "")).startswith("tasklet-followup-") for x in merged)


def test_workspace_summary_counts_tasklet_followups(tmp_path: Path) -> None:
    registry = {"ignore_paths": []}
    (tmp_path / "demo").mkdir()
    (tmp_path / "demo" / ".git").mkdir()
    tr = create_tasklet_run(
        tmp_path,
        tasklet_id="docs_health_remediation",
        tasklet_version=1,
        kind="docs_health_remediation",
        project_slug="demo",
        docs_health_session_id="sx",
        agent_runtime_session_id="ax",
        sandbox_backend="inline",
    )
    rid = str(tr["id"])
    try_apply_state_transition(tmp_path, rid, "preparing")
    try_apply_state_transition(tmp_path, rid, "running")
    try_apply_state_transition(tmp_path, rid, "failed", last_error="boom")

    summ = dh_store.workspace_summary(tmp_path, registry)
    assert summ.get("builtin_tasklets")
    row = next(x for x in summ["projects"] if x.get("project") == "demo")
    assert int(row.get("open_tasklet_followups") or 0) >= 1
    assert int(summ["rollup"].get("open_tasklet_followups_total") or 0) >= 1


def test_list_tasklet_runs_for_project_filters(tmp_path: Path) -> None:
    create_tasklet_run(
        tmp_path,
        tasklet_id="docs_health_remediation",
        tasklet_version=1,
        kind="docs_health_remediation",
        project_slug="alpha",
        docs_health_session_id="s1",
        agent_runtime_session_id="a",
        sandbox_backend="inline",
    )
    create_tasklet_run(
        tmp_path,
        tasklet_id="docs_health_remediation",
        tasklet_version=1,
        kind="docs_health_remediation",
        project_slug="beta",
        docs_health_session_id="s2",
        agent_runtime_session_id="b",
        sandbox_backend="inline",
    )
    alpha_runs = list_tasklet_runs_for_project(tmp_path, "alpha", limit=10)
    assert len(alpha_runs) == 1
    assert str(alpha_runs[0].get("project_slug")) == "alpha"
