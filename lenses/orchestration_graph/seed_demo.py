"""Load bundled demo graph when the DB is empty (idempotent)."""

from __future__ import annotations

import json
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from lenses.orchestration_graph.constants import EDGE_KINDS, ENTITY_KINDS


def _fixture_path() -> Path:
    return Path(__file__).resolve().parent.parent / "fixtures" / "orchestration-graph.demo.json"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def entity_count(conn: sqlite3.Connection) -> int:
    row = conn.execute("SELECT COUNT(*) AS c FROM ogs_entity").fetchone()
    return int(row["c"]) if row else 0


def apply_demo_bundle(conn: sqlite3.Connection, bundle: dict[str, Any]) -> dict[str, int]:
    """Replace demo-prefix entities/edges, then insert bundle rows (transaction)."""
    conn.execute("PRAGMA foreign_keys = ON")
    entities = bundle.get("entities")
    edges = bundle.get("edges")
    if not isinstance(entities, list) or not isinstance(edges, list):
        raise ValueError("bundle must have entities and edges arrays")

    conn.execute("DELETE FROM ogs_edge WHERE from_id LIKE 'ogs:demo:%' OR to_id LIKE 'ogs:demo:%'")
    conn.execute("DELETE FROM ogs_entity WHERE id LIKE 'ogs:demo:%'")

    now = _now_iso()
    for raw in entities:
        if not isinstance(raw, dict):
            continue
        eid = str(raw.get("id") or "").strip()
        kind = str(raw.get("kind") or "").strip()
        if not eid or kind not in ENTITY_KINDS:
            continue
        name = str(raw.get("display_name") or eid).strip()
        summary = str(raw.get("summary") or "")
        payload = raw.get("payload_json")
        if isinstance(payload, dict):
            payload_s = json.dumps(payload, separators=(",", ":"), sort_keys=True)
        elif isinstance(payload, str):
            payload_s = payload
        else:
            payload_s = "{}"
        ext = str(raw.get("external_ref") or "")
        src = str(raw.get("source_system") or "lenses_demo_seed")
        src_id = str(raw.get("source_record_id") or "")
        conn.execute(
            """
            INSERT INTO ogs_entity (
              id, kind, display_name, summary, payload_json, external_ref,
              source_system, source_record_id, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (eid, kind, name, summary, payload_s, ext, src, src_id, now, now),
        )

    for raw in edges:
        if not isinstance(raw, dict):
            continue
        eid = str(raw.get("id") or "").strip() or f"ogs:demo:edge:{uuid.uuid4().hex[:12]}"
        fr = str(raw.get("from_id") or "").strip()
        to = str(raw.get("to_id") or "").strip()
        kind = str(raw.get("kind") or "").strip()
        if not fr or not to or kind not in EDGE_KINDS:
            continue
        payload = raw.get("payload_json")
        if isinstance(payload, dict):
            payload_s = json.dumps(payload, separators=(",", ":"), sort_keys=True)
        elif isinstance(payload, str):
            payload_s = payload
        else:
            payload_s = "{}"
        src = str(raw.get("source_system") or "lenses_demo_seed")
        src_id = str(raw.get("source_record_id") or "")
        conn.execute(
            """
            INSERT OR REPLACE INTO ogs_edge (
              id, from_id, to_id, kind, payload_json, source_system, source_record_id, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (eid, fr, to, kind, payload_s, src, src_id, now),
        )

    conn.commit()
    return {"entities": len(entities), "edges": len(edges)}


def seed_from_demo_bundle_if_empty(conn: sqlite3.Connection) -> bool:
    """If there are no entities, load ``orchestration-graph.demo.json``. Returns whether seed ran."""
    if entity_count(conn) > 0:
        return False
    path = _fixture_path()
    if not path.is_file():
        return False
    try:
        bundle = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        return False
    if not isinstance(bundle, dict):
        return False
    apply_demo_bundle(conn, bundle)
    return True


def force_reload_demo(conn: sqlite3.Connection) -> dict[str, Any]:
    """Replace demo slice with fixture contents regardless of prior state."""
    path = _fixture_path()
    bundle = json.loads(path.read_text(encoding="utf-8"))
    stats = apply_demo_bundle(conn, bundle)
    return {"ok": True, "reloaded": True, **stats}
