"""Story → build → artifact → release → environment via orchestration graph."""

from __future__ import annotations

import json
from pathlib import Path

from lenses.orchestration_graph.cicd_trace import story_cicd_trace_from_graph
from lenses.orchestration_graph.migrate import apply_migrations
from lenses.orchestration_graph.seed_demo import apply_demo_bundle


def _conn(tmp_path: Path):
    import sqlite3

    d = tmp_path / ".lenses-local"
    d.mkdir()
    db = d / "ogs.sqlite"
    conn = sqlite3.connect(str(db))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    apply_migrations(conn)
    return conn


def test_cicd_trace_s1842(tmp_path: Path) -> None:
    conn = _conn(tmp_path)
    bundle = json.loads(
        (Path(__file__).resolve().parent.parent / "lenses" / "fixtures" / "orchestration-graph.demo.json").read_text(
            encoding="utf-8"
        )
    )
    apply_demo_bundle(conn, bundle)
    out = story_cicd_trace_from_graph(conn, "S-1842")
    conn.close()
    assert out["ok"] is True
    assert out.get("linked") is True
    assert len(out.get("builds") or []) >= 1
    assert len(out.get("artifacts") or []) >= 1
    assert len(out.get("releases") or []) >= 1
    assert len(out.get("deployments") or []) >= 1
