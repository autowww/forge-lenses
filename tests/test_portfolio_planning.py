"""Portfolio / scenario / critical-path helpers on the orchestration graph (Sprint 2)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from lenses.orchestration_graph.migrate import apply_migrations, current_schema_version
from lenses.orchestration_graph.portfolio import (
    compare_scenarios,
    critical_path_depends_on,
    portfolio_context_payload,
    portfolio_rollups,
)
from lenses.orchestration_graph.seed_demo import apply_demo_bundle


def _conn(tmp_path):
    import sqlite3

    local = tmp_path / ".lenses-local"
    local.mkdir(parents=True)
    db = local / "pogs.sqlite"
    conn = sqlite3.connect(str(db))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    apply_migrations(conn)
    return conn


def _demo_bundle() -> dict:
    p = Path(__file__).resolve().parent.parent / "lenses" / "fixtures" / "orchestration-graph.demo.json"
    return json.loads(p.read_text(encoding="utf-8"))


def test_portfolio_rollups_and_critical_path(tmp_path) -> None:
    conn = _conn(tmp_path)
    assert current_schema_version(conn) == 5
    apply_demo_bundle(conn, _demo_bundle())
    roll = portfolio_rollups(conn)
    assert roll["dependency_pressure_max"] >= 1
    cp = roll["critical_path"]
    assert cp["ok"] is True
    assert cp["length"] == pytest.approx(3.0)
    conn.close()


def test_compare_scenarios_baseline_stretch(tmp_path) -> None:
    conn = _conn(tmp_path)
    apply_demo_bundle(conn, _demo_bundle())
    cmp = compare_scenarios(
        conn,
        "ogs:demo:scenario:baseline",
        "ogs:demo:scenario:stretch",
    )
    assert cmp["ok"] is True
    assert cmp["delta_numeric"]["horizon_shift_days"] == -14.0
    conn.close()


def test_portfolio_context_payload_with_compare(tmp_path) -> None:
    conn = _conn(tmp_path)
    apply_demo_bundle(conn, _demo_bundle())
    out = portfolio_context_payload(
        conn,
        scenario_a="ogs:demo:scenario:baseline",
        scenario_b="ogs:demo:scenario:stretch",
        slip_focus_id="ogs:demo:story:oauth-refresh-ui",
    )
    assert out["ok"] is True
    assert out["scenario_compare"]["ok"] is True
    assert len(out["depends_on_edges"]) >= 1
    conn.close()


def test_critical_path_reports_cycle_placeholder(tmp_path) -> None:
    conn = _conn(tmp_path)
    apply_demo_bundle(conn, _demo_bundle())
    # Introduce a cycle on the two demo stories that participate in depends_on
    conn.execute(
        "INSERT OR REPLACE INTO ogs_edge (id, from_id, to_id, kind, payload_json, "
        "source_system, source_record_id, created_at) VALUES (?, ?, ?, 'depends_on', '{}', '', '', datetime('now'))",
        ("ogs:test:cycle", "ogs:demo:story:rate-limit-auth", "ogs:demo:story:oauth-refresh-ui"),
    )
    conn.commit()
    cp = critical_path_depends_on(conn)
    assert cp["ok"] is False
    assert cp["error"] == "cycle_in_depends_on"
    conn.close()
