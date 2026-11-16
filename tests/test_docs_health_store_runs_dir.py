"""Regression: first ``write_run`` must create ``runs/`` (empty reply / Failed to fetch if missing)."""

from __future__ import annotations

from pathlib import Path

from lenses.docs_health import store


def test_write_run_creates_runs_dir_on_first_persist(tmp_path: Path) -> None:
    ws = tmp_path / "ws"
    ws.mkdir()
    slug = "fresh_proj"
    store.ensure_store_dir(ws, slug)
    runs_path = ws / ".lenses-local" / "docs-health" / "fresh_proj" / "runs"
    assert not runs_path.exists()
    store.write_run(
        ws,
        slug,
        {
            "id": "run-e2e-1",
            "status": "completed",
            "finished_at": store.now_iso(),
            "finding_count": 0,
            "findings": [],
            "clusters": [],
            "score": {"value": 100},
        },
    )
    assert (runs_path / "run-e2e-1.json").is_file()
