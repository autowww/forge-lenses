"""Story → branch / PR / commit resolution via orchestration graph."""

from __future__ import annotations

import json
from pathlib import Path

from lenses.orchestration_graph.code_links import story_code_links_from_graph
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


def test_story_code_links_s1842(tmp_path: Path) -> None:
    conn = _conn(tmp_path)
    bundle = json.loads(
        (Path(__file__).resolve().parent.parent / "lenses" / "fixtures" / "orchestration-graph.demo.json").read_text(
            encoding="utf-8"
        )
    )
    apply_demo_bundle(conn, bundle)
    out = story_code_links_from_graph(conn, "S-1842")
    conn.close()
    assert out["ok"] is True
    assert out.get("linked") is True
    assert len(out.get("change_requests") or []) >= 1
    assert out["change_requests"][0].get("number") == 184
    assert len(out.get("branches") or []) >= 1
    assert out.get("merge_readiness") == "merged"


def test_story_code_links_missing_story(tmp_path: Path) -> None:
    conn = _conn(tmp_path)
    bundle = json.loads(
        (Path(__file__).resolve().parent.parent / "lenses" / "fixtures" / "orchestration-graph.demo.json").read_text(
            encoding="utf-8"
        )
    )
    apply_demo_bundle(conn, bundle)
    out = story_code_links_from_graph(conn, "S-NOT-IN-GRAPH")
    conn.close()
    assert out["ok"] is True
    assert out.get("linked") is False
