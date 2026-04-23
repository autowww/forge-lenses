"""Docs Health remediation session cancel and inactive guards."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from lenses.docs_health import store
from lenses.docs_health.api_handlers import post_project_docs_health


def _fixture_workspace(tmp_path: Path) -> tuple[Path, str]:
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
    return ws, slug


def test_session_cancel_sets_status_and_is_idempotent(tmp_path: Path) -> None:
    ws, slug = _fixture_workspace(tmp_path)
    registry: dict[str, Any] = {}
    bundle = {"can_read_project": True, "can_write_project": True}

    created: list[tuple[int, dict[str, Any]]] = []

    def send_create(code: int, body: dict[str, Any]) -> None:
        created.append((code, body))

    post_project_docs_health(
        ws,
        registry,
        slug,
        {"op": "create_session", "cluster_id": "cluster-1", "run_id": "runtest0001"},
        bundle=bundle,
        send_json=send_create,
    )
    assert len(created) == 1
    assert created[0][0] == 200
    sess_id = str(created[0][1]["session"]["id"])
    assert "display_name" in created[0][1]["session"]
    assert slug in str(created[0][1]["session"]["display_name"])

    out: list[tuple[int, dict[str, Any]]] = []

    def cap(code: int, body: dict[str, Any]) -> None:
        out.append((code, body))

    post_project_docs_health(
        ws,
        registry,
        slug,
        {"op": "session_cancel", "session_id": sess_id},
        bundle=bundle,
        send_json=cap,
    )
    assert out[-1][0] == 200
    assert out[-1][1]["session"]["status"] == "cancelled"
    assert out[-1][1]["session"].get("cancelled_at")

    post_project_docs_health(
        ws,
        registry,
        slug,
        {"op": "session_cancel", "session_id": sess_id},
        bundle=bundle,
        send_json=cap,
    )
    assert out[-1][0] == 200
    assert out[-1][1].get("already_cancelled") is True


def test_session_step_rejected_when_cancelled(tmp_path: Path) -> None:
    ws, slug = _fixture_workspace(tmp_path)
    registry: dict[str, Any] = {}
    bundle = {"can_read_project": True, "can_write_project": True}
    captured: list[tuple[int, dict[str, Any]]] = []

    def send_json(code: int, body: dict[str, Any]) -> None:
        captured.append((code, body))

    post_project_docs_health(
        ws,
        registry,
        slug,
        {"op": "create_session", "cluster_id": "cluster-1", "run_id": "runtest0001"},
        bundle=bundle,
        send_json=send_json,
    )
    sid = str(captured[0][1]["session"]["id"])
    captured.clear()

    post_project_docs_health(
        ws,
        registry,
        slug,
        {"op": "session_cancel", "session_id": sid},
        bundle=bundle,
        send_json=send_json,
    )
    captured.clear()

    post_project_docs_health(
        ws,
        registry,
        slug,
        {"op": "session_step", "session_id": sid, "step": "enrich"},
        bundle=bundle,
        send_json=send_json,
    )
    assert captured[-1][0] == 409
    assert captured[-1][1].get("error") == "session_not_active"


def test_session_cancel_works_without_repo_write_permission(tmp_path: Path) -> None:
    """Cancel only touches lenses-local session JSON (like enrich/review steps)."""
    ws, slug = _fixture_workspace(tmp_path)
    registry: dict[str, Any] = {}
    read_only = {"can_read_project": True, "can_write_project": False}
    captured: list[tuple[int, dict[str, Any]]] = []

    def send_json(code: int, body: dict[str, Any]) -> None:
        captured.append((code, body))

    post_project_docs_health(
        ws,
        registry,
        slug,
        {"op": "create_session", "cluster_id": "cluster-1", "run_id": "runtest0001"},
        bundle=read_only,
        send_json=send_json,
    )
    sid = str(captured[0][1]["session"]["id"])
    captured.clear()

    post_project_docs_health(
        ws,
        registry,
        slug,
        {"op": "session_cancel", "session_id": sid},
        bundle=read_only,
        send_json=send_json,
    )
    assert captured[-1][0] == 200
    assert captured[-1][1]["session"]["status"] == "cancelled"
