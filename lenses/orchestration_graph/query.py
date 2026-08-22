"""Graph traversal for traceability API responses."""

from __future__ import annotations

import json
import sqlite3
from collections import deque
from typing import Any, Literal

Direction = Literal["out", "in", "both"]


def _row_entity(row: sqlite3.Row) -> dict[str, Any]:
    payload = row["payload_json"]
    try:
        parsed = json.loads(payload) if isinstance(payload, str) else {}
    except json.JSONDecodeError:
        parsed = {}
    return {
        "id": row["id"],
        "kind": row["kind"],
        "display_name": row["display_name"],
        "summary": row["summary"] or "",
        "payload": parsed if isinstance(parsed, dict) else {},
        "external_ref": row["external_ref"] or "",
        "source_system": row["source_system"] or "",
        "source_record_id": row["source_record_id"] or "",
    }


def _row_edge(row: sqlite3.Row) -> dict[str, Any]:
    payload = row["payload_json"]
    try:
        parsed = json.loads(payload) if isinstance(payload, str) else {}
    except json.JSONDecodeError:
        parsed = {}
    return {
        "id": row["id"],
        "from_id": row["from_id"],
        "to_id": row["to_id"],
        "kind": row["kind"],
        "payload": parsed if isinstance(parsed, dict) else {},
        "source_system": row["source_system"] or "",
        "source_record_id": row["source_record_id"] or "",
    }


def fetch_entity(conn: sqlite3.Connection, entity_id: str) -> dict[str, Any] | None:
    row = conn.execute(
        "SELECT * FROM ogs_entity WHERE id = ?",
        (entity_id,),
    ).fetchone()
    return _row_entity(row) if row else None


def trace_subgraph(
    conn: sqlite3.Connection,
    root_id: str,
    *,
    direction: Direction = "both",
    max_depth: int = 5,
    max_nodes: int = 400,
) -> dict[str, Any]:
    """BFS from root collecting nodes and edges; caps size for UI safety."""
    root = fetch_entity(conn, root_id)
    if root is None:
        return {
            "ok": False,
            "error": "entity_not_found",
            "root_id": root_id,
            "nodes": [],
            "edges": [],
            "truncated": False,
        }

    max_depth = max(0, min(int(max_depth), 12))
    max_nodes = max(1, min(int(max_nodes), 2000))

    seen_nodes: set[str] = {root_id}
    seen_edges: set[str] = set()
    edge_rows: list[dict[str, Any]] = []
    q: deque[tuple[str, int]] = deque([(root_id, 0)])
    truncated = False

    while q and len(seen_nodes) < max_nodes:
        nid, depth = q.popleft()
        if depth >= max_depth:
            continue

        neighbors: list[tuple[sqlite3.Row, str]] = []
        if direction in ("out", "both"):
            for row in conn.execute(
                "SELECT * FROM ogs_edge WHERE from_id = ?",
                (nid,),
            ):
                neighbors.append((row, str(row["to_id"])))
        if direction in ("in", "both"):
            for row in conn.execute(
                "SELECT * FROM ogs_edge WHERE to_id = ?",
                (nid,),
            ):
                neighbors.append((row, str(row["from_id"])))

        stop_outer = False
        for row, other_id in neighbors:
            eid = str(row["id"])
            if eid not in seen_edges:
                seen_edges.add(eid)
                edge_rows.append(_row_edge(row))
            if other_id in seen_nodes:
                continue
            if len(seen_nodes) >= max_nodes:
                truncated = True
                stop_outer = True
                break
            seen_nodes.add(other_id)
            q.append((other_id, depth + 1))
        if stop_outer:
            break

    if len(seen_nodes) >= max_nodes:
        truncated = True

    placeholders = ",".join("?" * len(seen_nodes))
    rows = conn.execute(
        f"SELECT * FROM ogs_entity WHERE id IN ({placeholders})",
        tuple(sorted(seen_nodes)),
    ).fetchall()
    nodes = [_row_entity(r) for r in rows]
    nodes.sort(key=lambda x: x["id"])

    edge_rows.sort(key=lambda e: e["id"])

    return {
        "ok": True,
        "root_id": root_id,
        "root": root,
        "nodes": nodes,
        "edges": edge_rows,
        "truncated": truncated,
        "limits": {"max_depth": max_depth, "max_nodes": max_nodes},
    }
