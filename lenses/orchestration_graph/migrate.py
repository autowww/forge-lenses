"""Versioned DDL migrations for ``lenses-orchestration.sqlite``."""

from __future__ import annotations

import sqlite3

_SCHEMA_TABLE = "_ogs_schema"
_LATEST = 8


def current_schema_version(conn: sqlite3.Connection) -> int:
    row = conn.execute(
        f"SELECT version FROM {_SCHEMA_TABLE} WHERE id = 1"
    ).fetchone()
    return int(row[0]) if row else 0


def apply_migrations(conn: sqlite3.Connection) -> None:
    conn.execute(
        f"""
        CREATE TABLE IF NOT EXISTS {_SCHEMA_TABLE} (
          id INTEGER PRIMARY KEY CHECK (id = 1),
          version INTEGER NOT NULL
        )
        """
    )
    ver = current_schema_version(conn)
    if ver < 1:
        _migration_v1(conn)
    if ver < 2:
        _migration_v2(conn)
    if ver < 3:
        _migration_v3(conn)
    if ver < 4:
        _migration_v4(conn)
    if ver < 5:
        _migration_v5(conn)
    if ver < 6:
        _migration_v6(conn)
    if ver < 7:
        _migration_v7(conn)
    if ver < 8:
        _migration_v8(conn)
    conn.execute(
        f"INSERT OR REPLACE INTO {_SCHEMA_TABLE}(id, version) VALUES (1, ?)",
        (_LATEST,),
    )
    conn.commit()


def _migration_v1(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS ogs_entity (
          id TEXT PRIMARY KEY,
          kind TEXT NOT NULL,
          display_name TEXT NOT NULL,
          summary TEXT NOT NULL DEFAULT '',
          payload_json TEXT NOT NULL DEFAULT '{}',
          external_ref TEXT NOT NULL DEFAULT '',
          source_system TEXT NOT NULL DEFAULT '',
          source_record_id TEXT NOT NULL DEFAULT '',
          created_at TEXT NOT NULL,
          updated_at TEXT NOT NULL
        );

        CREATE INDEX IF NOT EXISTS idx_ogs_entity_kind ON ogs_entity(kind);
        CREATE INDEX IF NOT EXISTS idx_ogs_entity_source ON ogs_entity(source_system, source_record_id);

        CREATE TABLE IF NOT EXISTS ogs_edge (
          id TEXT PRIMARY KEY,
          from_id TEXT NOT NULL,
          to_id TEXT NOT NULL,
          kind TEXT NOT NULL,
          payload_json TEXT NOT NULL DEFAULT '{}',
          source_system TEXT NOT NULL DEFAULT '',
          source_record_id TEXT NOT NULL DEFAULT '',
          created_at TEXT NOT NULL,
          FOREIGN KEY (from_id) REFERENCES ogs_entity(id) ON DELETE CASCADE,
          FOREIGN KEY (to_id) REFERENCES ogs_entity(id) ON DELETE CASCADE
        );

        CREATE INDEX IF NOT EXISTS idx_ogs_edge_from ON ogs_edge(from_id);
        CREATE INDEX IF NOT EXISTS idx_ogs_edge_to ON ogs_edge(to_id);
        CREATE INDEX IF NOT EXISTS idx_ogs_edge_kind ON ogs_edge(kind);
        CREATE UNIQUE INDEX IF NOT EXISTS uq_ogs_edge_triple
          ON ogs_edge(from_id, to_id, kind);
        """
    )


def _migration_v2(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        CREATE INDEX IF NOT EXISTS idx_ogs_edge_kind_to ON ogs_edge(kind, to_id);
        CREATE INDEX IF NOT EXISTS idx_ogs_edge_kind_from ON ogs_edge(kind, from_id);
        """
    )


def _migration_v3(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS bridge_spine_overlay (
          entity_id TEXT PRIMARY KEY,
          canonical_kind TEXT NOT NULL,
          owner TEXT NOT NULL DEFAULT '',
          freshness_at TEXT NOT NULL DEFAULT '',
          trust_level TEXT NOT NULL DEFAULT 'inferred',
          workspace_scope TEXT NOT NULL DEFAULT '',
          project_slug TEXT NOT NULL DEFAULT '',
          provenance_json TEXT NOT NULL DEFAULT '{}',
          FOREIGN KEY (entity_id) REFERENCES ogs_entity(id) ON DELETE CASCADE
        );
        CREATE INDEX IF NOT EXISTS idx_bridge_overlay_canonical
          ON bridge_spine_overlay(canonical_kind);
        """
    )


def _migration_v4(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS bridge_evidence_doc_index (
          rel_path TEXT PRIMARY KEY,
          entity_id TEXT NOT NULL,
          checksum TEXT NOT NULL DEFAULT '',
          ingested_at TEXT NOT NULL,
          FOREIGN KEY (entity_id) REFERENCES ogs_entity(id) ON DELETE CASCADE
        );
        CREATE INDEX IF NOT EXISTS idx_bridge_evidence_entity
          ON bridge_evidence_doc_index(entity_id);
        """
    )


def _migration_v5(conn: sqlite3.Connection) -> None:
    """Sprint B3 agentic bridge — reserved for future agentic indexes; graph uses ogs_entity payload."""
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_ogs_entity_kind_updated
          ON ogs_entity(kind, updated_at);
        """
    )


def _migration_v6(conn: sqlite3.Connection) -> None:
    """Sprint B4 ceremony bridge — graph kinds only; optional query index for ceremony lists."""
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_ogs_entity_kind_created
          ON ogs_entity(kind, created_at);
        """
    )


def _migration_v7(conn: sqlite3.Connection) -> None:
    """Sprint B5 handoff bridge — partial index for handoff/return list queries."""
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_ogs_entity_handoff_session_return
          ON ogs_entity(kind, updated_at)
          WHERE kind IN (
            'handoff_package', 'execution_session', 'execution_return', 'sync_checkpoint'
          );
        """
    )


def _migration_v8(conn: sqlite3.Connection) -> None:
    """Sprint B6 PDLC outcome bridge — partial index for launch/outcome list queries."""
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_ogs_entity_outcome_launch
          ON ogs_entity(kind, updated_at)
          WHERE kind IN (
            'launch_record', 'learning_summary', 'followon_ore_candidate', 'outcome_signal'
          );
        """
    )
