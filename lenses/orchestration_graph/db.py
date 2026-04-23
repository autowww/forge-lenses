"""SQLite persistence for the orchestration graph under ``<workspace>/.lenses-local/``."""

from __future__ import annotations

import sqlite3
from pathlib import Path

from lenses.orchestration_graph.feature_flag import (
    experimental_orchestration_graph_enabled,
    orchestration_auto_seed_enabled,
)
from lenses.orchestration_graph.migrate import apply_migrations, current_schema_version
from lenses.orchestration_graph.seed_demo import seed_from_demo_bundle_if_empty


def orchestration_db_path(workspace_root: Path) -> Path:
    root = workspace_root.resolve()
    local = root / ".lenses-local"
    return local / "lenses-orchestration.sqlite"


def connect(workspace_root: Path) -> sqlite3.Connection | None:
    """Open DB, migrate, optionally auto-seed demo. Returns ``None`` if feature disabled."""
    if not experimental_orchestration_graph_enabled():
        return None
    path = orchestration_db_path(workspace_root)
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path), timeout=30.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    apply_migrations(conn)
    if orchestration_auto_seed_enabled():
        seed_from_demo_bundle_if_empty(conn)
    return conn


def graph_stats(conn: sqlite3.Connection) -> dict[str, int | str]:
    ver = current_schema_version(conn)
    n_e = int(conn.execute("SELECT COUNT(*) AS c FROM ogs_entity").fetchone()["c"])
    n_ed = int(conn.execute("SELECT COUNT(*) AS c FROM ogs_edge").fetchone()["c"])
    return {"schema_version": ver, "entity_count": n_e, "edge_count": n_ed}
