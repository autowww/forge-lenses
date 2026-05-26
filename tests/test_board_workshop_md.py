"""Workshop kickoff Markdown → sticker board prefill."""

from __future__ import annotations

from pathlib import Path

import pytest

from lenses.board_workshop_md import (
    hydrate_board_from_workshop_md,
    parse_workshop_kickoff_markdown,
)
from lenses.sticker_board import initial_state_for_session, registry_apply

FIXTURE = Path(__file__).resolve().parent / "fixtures" / "workshop_kickoff_a11y.md"


def test_workshop_kickoff_template_columns() -> None:
    state = initial_state_for_session("workshop_kickoff", "local")
    col_ids = {c["id"] for c in state["columns"]}
    assert state["session_template"] == "workshop_kickoff"
    assert col_ids >= {"discuss", "core_mvp", "support", "proof", "later", "decide", "parking"}


def test_parse_kickoff_fixture_sections() -> None:
    text = FIXTURE.read_text(encoding="utf-8")
    parsed = parse_workshop_kickoff_markdown(text)
    sections = set(parsed.get("sections") or [])
    assert "validation_board" in sections
    assert "feature_map" in sections
    assert "agenda" in sections
    assert "journey" in sections
    stickers = parsed.get("stickers") or []
    assert len(stickers) >= 20
    kinds = {s.get("source_kind") for s in stickers}
    assert "validation_decision" in kinds
    assert "feature_area" in kinds
    assert "agenda_block" in kinds
    assert "journey_stage" in kinds


def test_hydrate_adds_stickers_to_board() -> None:
    text = FIXTURE.read_text(encoding="utf-8")
    state = initial_state_for_session("workshop_kickoff", "local")
    state, meta = hydrate_board_from_workshop_md(
        Path("/tmp"),
        state,
        workshop_md_text=text,
    )
    assert meta["prefill_ok"] is True
    assert meta["prefill_message"] == "ok"
    assert len(state["stickers"]) >= 20
    assert state["prefill_applied"] is True


def test_registry_create_workshop_kickoff_from_text(tmp_path: Path) -> None:
    text = FIXTURE.read_text(encoding="utf-8")
    ws = tmp_path
    scan = {"children": [{"name": "demo"}], "wbs": [], "roadmaps": []}
    ok, err, extra = registry_apply(
        ws,
        None,
        {"demo"},
        "create",
        {
            "project": "demo",
            "label": "A11y kickoff",
            "storage": "local",
            "session_template": "workshop_kickoff",
            "workshop_md_text": text,
            "prefill": True,
        },
    )
    assert ok, err
    assert extra and extra.get("board_id")
    prefill = extra.get("prefill") or {}
    assert prefill.get("prefill_ok") is True
    assert (prefill.get("stickers_added") or 0) >= 20


def test_registry_create_workshop_kickoff_from_path(tmp_path: Path) -> None:
    ws = tmp_path
    md = ws / "ember-logs" / "kickoff.md"
    md.parent.mkdir(parents=True)
    md.write_text(FIXTURE.read_text(encoding="utf-8"), encoding="utf-8")
    scan = {"children": [{"name": "demo"}], "wbs": [], "roadmaps": []}
    ok, err, extra = registry_apply(
        ws,
        None,
        {"demo"},
        "create",
        {
            "project": "demo",
            "label": "Kickoff from path",
            "storage": "local",
            "session_template": "workshop_kickoff",
            "workshop_md_path": "ember-logs/kickoff.md",
            "prefill": True,
        },
    )
    assert ok, err
    assert extra and extra.get("prefill_message") in (None, "ok", "")
