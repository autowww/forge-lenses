"""Trace, impact, provenance, gaps, and graph-completeness scoring for the bridge spine."""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from typing import Any, Literal

import sqlite3

from lenses.bridge.overlay import fetch_overlay
from lenses.bridge.projection import project_entity
from lenses.bridge.registry import BridgeRegistry
from lenses.orchestration_graph.constants import EDGE_KINDS
from lenses.orchestration_graph.query import _row_edge, fetch_entity, trace_subgraph

Direction = Literal["out", "in", "both"]


def _entity_ts_map(conn: sqlite3.Connection, entity_ids: set[str]) -> dict[str, dict[str, str]]:
    if not entity_ids:
        return {}
    ids = sorted(entity_ids)
    ph = ",".join("?" * len(ids))
    rows = conn.execute(
        f"SELECT id, created_at, updated_at FROM ogs_entity WHERE id IN ({ph})",
        tuple(ids),
    ).fetchall()
    return {
        str(r["id"]): {
            "created_at": str(r["created_at"] or ""),
            "updated_at": str(r["updated_at"] or ""),
        }
        for r in rows
    }


def spine_meta_for_entity(conn: sqlite3.Connection, entity_id: str) -> dict[str, Any]:
    """Provenance-oriented timestamps plus optional ``bridge_spine_overlay`` row."""
    ts_map = _entity_ts_map(conn, {entity_id})
    ov = fetch_overlay(conn, entity_id)
    return _spine_meta_for_node(entity_id, ts_map, ov)


def _spine_meta_for_node(
    entity_id: str,
    ts_map: dict[str, dict[str, str]],
    overlay: dict[str, Any] | None,
) -> dict[str, Any]:
    ts = ts_map.get(entity_id, {})
    meta: dict[str, Any] = {
        "created_at": ts.get("created_at", ""),
        "updated_at": ts.get("updated_at", ""),
        "owner": "",
        "freshness_at": "",
        "trust_level": "",
        "workspace_scope": "",
        "project_slug": "",
    }
    if overlay:
        meta["owner"] = overlay.get("owner") or ""
        meta["freshness_at"] = overlay.get("freshness_at") or ""
        meta["trust_level"] = overlay.get("trust_level") or ""
        meta["workspace_scope"] = overlay.get("workspace_scope") or ""
        meta["project_slug"] = overlay.get("project_slug") or ""
        if overlay.get("provenance"):
            meta["provenance"] = overlay["provenance"]
    return meta


def immediate_neighbors(
    conn: sqlite3.Connection,
    entity_id: str,
    reg: BridgeRegistry,
    *,
    max_neighbor_entities: int = 200,
) -> dict[str, Any]:
    """Single-hop edges and resolved neighbor entity rows (lightweight trace slice)."""
    ent = fetch_entity(conn, entity_id)
    if ent is None:
        return {"ok": False, "error": "entity_not_found", "entity_id": entity_id}
    out_e: list[dict[str, Any]] = []
    in_e: list[dict[str, Any]] = []
    for row in conn.execute("SELECT * FROM ogs_edge WHERE from_id = ?", (entity_id,)):
        out_e.append(_row_edge(row))
    for row in conn.execute("SELECT * FROM ogs_edge WHERE to_id = ?", (entity_id,)):
        in_e.append(_row_edge(row))
    neigh_ids: set[str] = set()
    for e in out_e:
        neigh_ids.add(str(e["to_id"]))
    for e in in_e:
        neigh_ids.add(str(e["from_id"]))
    neigh_ids.discard(entity_id)
    neighbor_entities: list[dict[str, Any]] = []
    ts_map = _entity_ts_map(conn, neigh_ids | {entity_id})
    for nid in sorted(neigh_ids)[:max_neighbor_entities]:
        fe = fetch_entity(conn, nid)
        if fe is None:
            continue
        ov = fetch_overlay(conn, nid)
        neighbor_entities.append(
            {
                **fe,
                "canonical_kind": reg.ogs_kind_to_canonical(str(fe.get("kind") or "")),
                "overlay": ov,
                "spine_meta": _spine_meta_for_node(nid, ts_map, ov),
            }
        )
    return {
        "ok": True,
        "entity_id": entity_id,
        "root": ent,
        "outgoing_edges": out_e,
        "incoming_edges": in_e,
        "neighbor_entities": neighbor_entities,
        "registry_version": reg.registry_version,
    }


def _edge_kind_sets(conn: sqlite3.Connection, entity_id: str) -> tuple[set[str], set[str]]:
    out_k: set[str] = set()
    in_k: set[str] = set()
    for row in conn.execute("SELECT kind FROM ogs_edge WHERE from_id = ?", (entity_id,)):
        out_k.add(str(row["kind"]))
    for row in conn.execute("SELECT kind FROM ogs_edge WHERE to_id = ?", (entity_id,)):
        in_k.add(str(row["kind"]))
    return out_k, in_k


def compute_gaps(conn: sqlite3.Connection, entity_id: str, reg: BridgeRegistry) -> dict[str, Any]:
    ent = fetch_entity(conn, entity_id)
    if ent is None:
        return {"ok": False, "error": "entity_not_found", "gaps": []}
    canonical = reg.ogs_kind_to_canonical(str(ent.get("kind") or ""))
    rules = reg.trace_rules(canonical)
    out_k, in_k = _edge_kind_sets(conn, entity_id)
    gaps: list[dict[str, Any]] = []
    for ek in rules["recommended_in"]:
        if ek not in in_k:
            gaps.append(
                {
                    "kind": "missing_incoming_edge",
                    "edge_kind": ek,
                    "canonical_kind": canonical,
                    "detail": f"No incoming `{ek}` edge — chain may be incomplete upstream.",
                }
            )
    for ek in rules["recommended_out"]:
        if ek not in out_k:
            gaps.append(
                {
                    "kind": "missing_outgoing_edge",
                    "edge_kind": ek,
                    "canonical_kind": canonical,
                    "detail": f"No outgoing `{ek}` edge — evidence or downstream link may be missing.",
                }
            )
    return {"ok": True, "entity_id": entity_id, "canonical_kind": canonical, "gaps": gaps}


def compute_traceability_score(conn: sqlite3.Connection, entity_id: str, reg: BridgeRegistry) -> dict[str, Any]:
    ent = fetch_entity(conn, entity_id)
    if ent is None:
        return {"ok": False, "error": "entity_not_found"}
    canonical = reg.ogs_kind_to_canonical(str(ent.get("kind") or ""))
    rules = reg.trace_rules(canonical)
    out_k, in_k = _edge_kind_sets(conn, entity_id)
    wanted_in = list(rules["recommended_in"])
    wanted_out = list(rules["recommended_out"])
    total = len(wanted_in) + len(wanted_out)
    if total == 0:
        score = 1.0
        matched = 0
    else:
        matched = sum(1 for x in wanted_in if x in in_k) + sum(1 for x in wanted_out if x in out_k)
        score = round(matched / total, 4)
    return {
        "ok": True,
        "entity_id": entity_id,
        "canonical_kind": canonical,
        "score": score,
        "matched_rules": matched,
        "total_rules": total,
        "present_in": sorted(in_k),
        "present_out": sorted(out_k),
    }


def bridge_trace_payload(
    conn: sqlite3.Connection,
    root_id: str,
    reg: BridgeRegistry,
    *,
    max_depth: int = 8,
    max_nodes: int = 500,
) -> dict[str, Any]:
    base = trace_subgraph(conn, root_id, direction="both", max_depth=max_depth, max_nodes=max_nodes)
    if not base.get("ok"):
        return {**base, "bridge": None}
    nodes = base.get("nodes") or []
    edges = base.get("edges") or []
    ts_map = _entity_ts_map(conn, {str(n.get("id") or "") for n in nodes if n.get("id")})
    enriched_nodes: list[dict[str, Any]] = []
    for n in nodes:
        nid = str(n.get("id") or "")
        ov = fetch_overlay(conn, nid)
        enriched_nodes.append(
            {
                **n,
                "canonical_kind": reg.ogs_kind_to_canonical(str(n.get("kind") or "")),
                "overlay": ov,
                "spine_meta": _spine_meta_for_node(nid, ts_map, ov),
                "projections": {
                    "neutral": project_entity(n, reg, "neutral"),
                    "forge": project_entity(n, reg, "forge"),
                    "sdlc": project_entity(n, reg, "sdlc"),
                    "pdlc": project_entity(n, reg, "pdlc"),
                },
            }
        )
    score = compute_traceability_score(conn, root_id, reg)
    gaps = compute_gaps(conn, root_id, reg)
    root_raw = base.get("root")
    root_enriched: dict[str, Any] | None = None
    if isinstance(root_raw, dict) and root_raw.get("id"):
        rid = str(root_raw["id"])
        rov = fetch_overlay(conn, rid)
        rts = _entity_ts_map(conn, {rid})
        root_enriched = {
            **root_raw,
            "canonical_kind": reg.ogs_kind_to_canonical(str(root_raw.get("kind") or "")),
            "overlay": rov,
            "spine_meta": _spine_meta_for_node(rid, rts, rov),
            "projections": {
                "neutral": project_entity(root_raw, reg, "neutral"),
                "forge": project_entity(root_raw, reg, "forge"),
                "sdlc": project_entity(root_raw, reg, "sdlc"),
                "pdlc": project_entity(root_raw, reg, "pdlc"),
            },
        }
    return {
        **base,
        **({"root": root_enriched} if root_enriched is not None else {}),
        "nodes": enriched_nodes,
        "bridge": {
            "registry_version": reg.registry_version,
            "traceability_score": score,
            "root_gaps": gaps.get("gaps") if gaps.get("ok") else [],
        },
    }


def bridge_impact_payload(
    conn: sqlite3.Connection,
    root_id: str,
    reg: BridgeRegistry,
    *,
    max_depth: int = 8,
    max_nodes: int = 400,
) -> dict[str, Any]:
    base = trace_subgraph(conn, root_id, direction="out", max_depth=max_depth, max_nodes=max_nodes)
    if not base.get("ok"):
        return {**base, "bridge": None}
    score = compute_traceability_score(conn, root_id, reg)
    return {
        **base,
        "bridge": {
            "registry_version": reg.registry_version,
            "direction": "downstream_impact",
            "traceability_score": score,
        },
    }


def bridge_provenance_payload(
    conn: sqlite3.Connection,
    root_id: str,
    reg: BridgeRegistry,
    *,
    max_depth: int = 8,
    max_nodes: int = 400,
) -> dict[str, Any]:
    base = trace_subgraph(conn, root_id, direction="in", max_depth=max_depth, max_nodes=max_nodes)
    if not base.get("ok"):
        return {**base, "bridge": None}
    score = compute_traceability_score(conn, root_id, reg)
    return {
        **base,
        "bridge": {
            "registry_version": reg.registry_version,
            "direction": "upstream_provenance",
            "traceability_score": score,
        },
    }


def insert_bridge_link(
    conn: sqlite3.Connection,
    *,
    from_id: str,
    to_id: str,
    kind: str,
    source_system: str = "bridge_api",
    source_record_id: str = "",
    payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if kind not in EDGE_KINDS:
        return {"ok": False, "error": "invalid_edge_kind", "allowed_sample": sorted(EDGE_KINDS)[:12]}
    fr = fetch_entity(conn, from_id)
    to = fetch_entity(conn, to_id)
    if fr is None or to is None:
        return {"ok": False, "error": "entity_not_found"}

    eid = f"ogs:bridge:{uuid.uuid4().hex[:16]}"
    payload_s = json.dumps(payload or {}, separators=(",", ":"), sort_keys=True)
    now = datetime.now(timezone.utc).isoformat()
    try:
        conn.execute(
            """
            INSERT INTO ogs_edge (
              id, from_id, to_id, kind, payload_json, source_system, source_record_id, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (eid, from_id, to_id, kind, payload_s, source_system, source_record_id, now),
        )
        conn.commit()
    except sqlite3.IntegrityError as ex:
        return {"ok": False, "error": "edge_exists_or_constraint", "detail": str(ex)}
    return {"ok": True, "edge_id": eid}
