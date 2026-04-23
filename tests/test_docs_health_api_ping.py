"""Docs Health POST API: lightweight connectivity check."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from lenses.docs_health.api_handlers import post_project_docs_health


def test_post_docs_health_ping_returns_ok(tmp_path: Path) -> None:
    ws = tmp_path / "ws"
    ws.mkdir()
    proj = ws / "demo"
    proj.mkdir()
    (proj / ".git").mkdir()

    captured: list[tuple[int, dict[str, Any]]] = []

    def send_json(code: int, body: dict[str, Any]) -> None:
        captured.append((code, body))

    post_project_docs_health(
        ws,
        {},
        "demo",
        {"op": "ping"},
        bundle={"can_read_project": True, "can_write_project": False},
        send_json=send_json,
    )
    assert len(captured) == 1
    code, payload = captured[0]
    assert code == 200
    assert payload["ok"] is True
    assert payload["op"] == "ping"
    assert payload["project"] == "demo"
    assert payload["repo_has_git"] is True
