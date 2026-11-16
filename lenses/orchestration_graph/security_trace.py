"""Story ↔ security findings, exceptions, controls, releases (orchestration graph)."""

from __future__ import annotations

import sqlite3
from typing import Any

from lenses.orchestration_graph.cicd_trace import story_cicd_trace_from_graph
from lenses.orchestration_graph.portfolio import story_entity_index
from lenses.orchestration_graph.query import fetch_entity


def story_security_trace_from_graph(conn: sqlite3.Connection, wbs_story_id: str) -> dict[str, Any]:
    sid = (wbs_story_id or "").strip()
    if not sid:
        return {"ok": False, "error": "missing_story_id"}

    idx = story_entity_index(conn)
    story_eid = idx.get(sid)
    if not story_eid:
        return {"ok": True, "linked": False, "story_id": sid}

    findings: list[dict[str, Any]] = []
    for r in conn.execute(
        "SELECT from_id FROM ogs_edge WHERE kind = ? AND to_id = ?",
        ("affects", story_eid),
    ):
        fid = str(r["from_id"])
        ent = fetch_entity(conn, fid)
        if ent and ent.get("kind") == "security_finding":
            findings.append(
                {
                    "entity_id": fid,
                    "display_name": ent.get("display_name"),
                    "payload": ent.get("payload") or {},
                    "external_ref": ent.get("external_ref"),
                }
            )

    exceptions: list[dict[str, Any]] = []
    seen_ex: set[str] = set()
    for f in findings:
        fid = str(f["entity_id"])
        for r2 in conn.execute(
            "SELECT from_id FROM ogs_edge WHERE kind = ? AND to_id = ?",
            ("accepted_risk_for", fid),
        ):
            xid = str(r2["from_id"])
            if xid in seen_ex:
                continue
            xent = fetch_entity(conn, xid)
            if xent and xent.get("kind") == "compliance_exception":
                seen_ex.add(xid)
                exceptions.append(
                    {
                        "entity_id": xid,
                        "display_name": xent.get("display_name"),
                        "payload": xent.get("payload") or {},
                        "external_ref": xent.get("external_ref"),
                    }
                )

    ctrace = story_cicd_trace_from_graph(conn, sid)
    release_rows = ctrace.get("releases") or [] if ctrace.get("ok") else []

    controls: list[dict[str, Any]] = []
    seen_c: set[str] = set()
    for rel in release_rows:
        rid = str(rel.get("entity_id") or "")
        if not rid:
            continue
        for r3 in conn.execute(
            "SELECT from_id FROM ogs_edge WHERE kind = ? AND to_id = ?",
            ("satisfies", rid),
        ):
            cid = str(r3["from_id"])
            if cid in seen_c:
                continue
            cent = fetch_entity(conn, cid)
            if cent and cent.get("kind") == "control":
                seen_c.add(cid)
                controls.append(
                    {
                        "entity_id": cid,
                        "display_name": cent.get("display_name"),
                        "payload": cent.get("payload") or {},
                        "external_ref": cent.get("external_ref"),
                        "for_release_entity_id": rid,
                    }
                )

    return {
        "ok": True,
        "linked": True,
        "story_id": sid,
        "story_entity_id": story_eid,
        "security_findings": findings,
        "compliance_exceptions": exceptions,
        "controls_for_releases": controls,
        "releases_from_delivery": [{"entity_id": r.get("entity_id"), "display_name": r.get("display_name")} for r in release_rows],
    }
