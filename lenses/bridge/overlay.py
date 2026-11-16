"""Optional per-entity spine overlay (owner, freshness, trust) in SQLite."""

from __future__ import annotations

import json
import sqlite3
from typing import Any


def fetch_overlay(conn: sqlite3.Connection, entity_id: str) -> dict[str, Any] | None:
    row = conn.execute(
        "SELECT * FROM bridge_spine_overlay WHERE entity_id = ?",
        (entity_id,),
    ).fetchone()
    if row is None:
        return None
    prov: dict[str, Any] = {}
    try:
        p = json.loads(row["provenance_json"] or "{}")
        if isinstance(p, dict):
            prov = p
    except json.JSONDecodeError:
        pass
    return {
        "entity_id": row["entity_id"],
        "canonical_kind": row["canonical_kind"],
        "owner": row["owner"] or "",
        "freshness_at": row["freshness_at"] or "",
        "trust_level": row["trust_level"] or "inferred",
        "workspace_scope": row["workspace_scope"] or "",
        "project_slug": row["project_slug"] or "",
        "provenance": prov,
    }


def upsert_overlay(
    conn: sqlite3.Connection,
    *,
    entity_id: str,
    canonical_kind: str,
    owner: str = "",
    freshness_at: str = "",
    trust_level: str = "inferred",
    workspace_scope: str = "",
    project_slug: str = "",
    provenance: dict[str, Any] | None = None,
) -> None:
    prov_s = json.dumps(provenance or {}, separators=(",", ":"), sort_keys=True)
    conn.execute(
        """
        INSERT INTO bridge_spine_overlay (
          entity_id, canonical_kind, owner, freshness_at, trust_level,
          workspace_scope, project_slug, provenance_json
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(entity_id) DO UPDATE SET
          canonical_kind = excluded.canonical_kind,
          owner = excluded.owner,
          freshness_at = excluded.freshness_at,
          trust_level = excluded.trust_level,
          workspace_scope = excluded.workspace_scope,
          project_slug = excluded.project_slug,
          provenance_json = excluded.provenance_json
        """,
        (
            entity_id,
            canonical_kind,
            owner,
            freshness_at,
            trust_level,
            workspace_scope,
            project_slug,
            prov_s,
        ),
    )
    conn.commit()
