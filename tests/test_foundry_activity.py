"""Tests for Foundry activity log."""

from pathlib import Path


def test_append_and_sync_phase(tmp_path: Path):
    from lenses.foundry.activity import append_activity, bootstrap_run_activity, sync_phase_progress
    from lenses.foundry.store import create_run_record, load_run, save_run, touch_run

    record = create_run_record(
        goal="fix multiply",
        target=str(tmp_path / "proj"),
        level="L1",
        execution_mode="draft",
        project="proj",
    )
    (tmp_path / "proj").mkdir()
    save_run(tmp_path, touch_run(record, status="running"))

    bootstrap_run_activity(tmp_path, record["id"], goal="fix multiply", worker="fake", project="proj")
    loaded = load_run(tmp_path, record["id"])
    assert loaded
    assert len(loaded.get("activity") or []) >= 3

    class Phase:
        name = "context"
        status = "ok"
        detail = "8 items"

    sync_phase_progress(tmp_path, record["id"], Phase())
    loaded2 = load_run(tmp_path, record["id"])
    assert any("context" in str(a.get("text", "")).lower() for a in loaded2.get("activity") or [])
    assert any(p.get("id") == "context" for p in loaded2.get("phases") or [])
