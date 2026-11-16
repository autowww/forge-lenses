"""Sticker board session templates and board v3 scoring fields."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from lenses.sticker_board import (
    BOARD_VERSION,
    initial_state_for_session,
    load_registry_raw,
    registry_apply,
    validate_board,
)


def test_roadmap_session_has_horizon_columns() -> None:
    state = initial_state_for_session("roadmap_session", "local")
    assert state["template"] == "kanban"
    assert state["session_template"] == "roadmap_session"
    col_ids = {c["id"] for c in state["columns"]}
    assert col_ids >= {"now", "next", "later", "parking"}
    assert len(state["stickers"]) >= 1


def test_product_map_session_columns() -> None:
    state = initial_state_for_session("product_map_workshop", "local")
    col_ids = {c["id"] for c in state["columns"]}
    assert "capabilities" in col_ids
    assert "journey" in col_ids


def test_workshop_kickoff_session_columns() -> None:
    state = initial_state_for_session("workshop_kickoff", "local")
    col_ids = {c["id"] for c in state["columns"]}
    assert state["session_template"] == "workshop_kickoff"
    assert "discuss" in col_ids
    assert "core_mvp" in col_ids
    assert "decide" in col_ids


def test_validate_board_impact_effort() -> None:
    state = initial_state_for_session("roadmap_session", "local")
    state["stickers"] = [
        {
            "id": "s-abc12345",
            "title": "T",
            "body": "",
            "column_id": "now",
            "order": 0,
            "x": 0,
            "y": 0,
            "impact": 4,
            "effort": 2,
        }
    ]
    ok, err = validate_board(state, None)
    assert ok, err


def test_validate_board_rejects_bad_impact() -> None:
    state = initial_state_for_session("roadmap_session", "local")
    state["stickers"][0] = {
        "id": "s-abc12345",
        "title": "T",
        "body": "",
        "column_id": "now",
        "order": 0,
        "x": 0,
        "y": 0,
        "impact": 9,
    }
    ok, err = validate_board(state, None)
    assert not ok
    assert "impact" in err


def test_registry_create_session_template(tmp_path: Path) -> None:
    ws = tmp_path
    scan = {"children": [{"name": "demo"}], "wbs": [], "roadmaps": []}
    ok, err, extra = registry_apply(
        ws,
        None,
        {"demo"},
        "create",
        {
            "project": "demo",
            "label": "Roadmap",
            "storage": "local",
            "session_template": "roadmap_session",
        },
    )
    assert ok, err
    assert extra and extra.get("board_id")
    reg = load_registry_raw(ws)
    bid = extra["board_id"]
    board_path = ws / ".lenses-local" / "sticker-boards" / f"{bid}.json"
    assert board_path.is_file()
    data = json.loads(board_path.read_text())
    assert data["session_template"] == "roadmap_session"
    assert data["version"] == BOARD_VERSION
