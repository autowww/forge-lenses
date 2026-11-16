"""Story ↔ production incidents, releases, services, postmortems (Sprint 8)."""

from __future__ import annotations

import sqlite3
from typing import Any

from lenses.orchestration_graph.portfolio import story_entity_index
from lenses.orchestration_graph.query import fetch_entity


def story_ops_trace_from_graph(conn: sqlite3.Connection, wbs_story_id: str) -> dict[str, Any]:
    sid = (wbs_story_id or "").strip()
    if not sid:
        return {"ok": False, "error": "missing_story_id"}

    idx = story_entity_index(conn)
    story_eid = idx.get(sid)
    if not story_eid:
        return {"ok": True, "linked": False, "story_id": sid}

    incidents: list[dict[str, Any]] = []
    for r in conn.execute(
        "SELECT from_id FROM ogs_edge WHERE kind = ? AND to_id = ?",
        ("affects", story_eid),
    ):
        iid = str(r["from_id"])
        ent = fetch_entity(conn, iid)
        if ent and ent.get("kind") == "incident":
            incidents.append(
                {
                    "entity_id": iid,
                    "display_name": ent.get("display_name"),
                    "payload": ent.get("payload") or {},
                    "external_ref": ent.get("external_ref"),
                }
            )

    releases: list[dict[str, Any]] = []
    seen_r: set[str] = set()
    for inc in incidents:
        iid = str(inc["entity_id"])
        for r2 in conn.execute(
            "SELECT to_id FROM ogs_edge WHERE kind = ? AND from_id = ?",
            ("triggered_after", iid),
        ):
            rid = str(r2["to_id"])
            if rid in seen_r:
                continue
            rent = fetch_entity(conn, rid)
            if rent and rent.get("kind") == "release":
                seen_r.add(rid)
                releases.append(
                    {
                        "entity_id": rid,
                        "display_name": rent.get("display_name"),
                        "payload": rent.get("payload") or {},
                        "external_ref": rent.get("external_ref"),
                    }
                )

    services: list[dict[str, Any]] = []
    seen_s: set[str] = set()
    for inc in incidents:
        iid = str(inc["entity_id"])
        for r3 in conn.execute(
            "SELECT to_id FROM ogs_edge WHERE kind = ? AND from_id = ?",
            ("impacts", iid),
        ):
            sid2 = str(r3["to_id"])
            if sid2 in seen_s:
                continue
            sent = fetch_entity(conn, sid2)
            if sent and sent.get("kind") == "service":
                seen_s.add(sid2)
                services.append(
                    {
                        "entity_id": sid2,
                        "display_name": sent.get("display_name"),
                        "payload": sent.get("payload") or {},
                        "external_ref": sent.get("external_ref"),
                    }
                )

    postmortems: list[dict[str, Any]] = []
    seen_p: set[str] = set()
    for inc in incidents:
        iid = str(inc["entity_id"])
        for r4 in conn.execute(
            "SELECT from_id FROM ogs_edge WHERE kind = ? AND to_id = ?",
            ("analyzes", iid),
        ):
            pid = str(r4["from_id"])
            if pid in seen_p:
                continue
            pent = fetch_entity(conn, pid)
            if pent and pent.get("kind") == "postmortem":
                seen_p.add(pid)
                postmortems.append(
                    {
                        "entity_id": pid,
                        "display_name": pent.get("display_name"),
                        "payload": pent.get("payload") or {},
                        "external_ref": pent.get("external_ref"),
                    }
                )

    return {
        "ok": True,
        "linked": True,
        "story_id": sid,
        "story_entity_id": story_eid,
        "incidents": incidents,
        "releases_from_incidents": releases,
        "services_impacted": services,
        "postmortems": postmortems,
    }
