"""Story → build → artifact → release → environment (canonical SDLC chain in the graph)."""

from __future__ import annotations

import sqlite3
from typing import Any

from lenses.orchestration_graph.portfolio import story_entity_index
from lenses.orchestration_graph.query import fetch_entity


def story_cicd_trace_from_graph(conn: sqlite3.Connection, wbs_story_id: str) -> dict[str, Any]:
    sid = (wbs_story_id or "").strip()
    if not sid:
        return {"ok": False, "error": "missing_story_id"}

    idx = story_entity_index(conn)
    story_eid = idx.get(sid)
    if not story_eid:
        return {"ok": True, "linked": False, "story_id": sid}

    builds: list[dict[str, Any]] = []
    for r in conn.execute(
        "SELECT from_id FROM ogs_edge WHERE kind = ? AND to_id = ?",
        ("tests", story_eid),
    ):
        bid = str(r["from_id"])
        ent = fetch_entity(conn, bid)
        if ent and ent.get("kind") == "build":
            builds.append(
                {
                    "entity_id": bid,
                    "display_name": ent.get("display_name"),
                    "payload": ent.get("payload") or {},
                    "external_ref": ent.get("external_ref"),
                }
            )

    artifacts: list[dict[str, Any]] = []
    seen_art: set[str] = set()
    for b in builds:
        bid = str(b["entity_id"])
        for r2 in conn.execute(
            "SELECT to_id FROM ogs_edge WHERE kind = ? AND from_id = ?",
            ("contains", bid),
        ):
            aid = str(r2["to_id"])
            if aid in seen_art:
                continue
            aent = fetch_entity(conn, aid)
            if aent and aent.get("kind") == "artifact":
                seen_art.add(aid)
                artifacts.append(
                    {
                        "entity_id": aid,
                        "display_name": aent.get("display_name"),
                        "payload": aent.get("payload") or {},
                        "external_ref": aent.get("external_ref"),
                    }
                )

    releases: list[dict[str, Any]] = []
    seen_rel: set[str] = set()
    for a in artifacts:
        aid = str(a["entity_id"])
        for r3 in conn.execute(
            "SELECT from_id FROM ogs_edge WHERE kind = ? AND to_id = ?",
            ("contains", aid),
        ):
            rid = str(r3["from_id"])
            if rid in seen_rel:
                continue
            rent = fetch_entity(conn, rid)
            if rent and rent.get("kind") == "release":
                seen_rel.add(rid)
                releases.append(
                    {
                        "entity_id": rid,
                        "display_name": rent.get("display_name"),
                        "payload": rent.get("payload") or {},
                        "external_ref": rent.get("external_ref"),
                    }
                )

    deployments: list[dict[str, Any]] = []
    for rel in releases:
        rid = str(rel["entity_id"])
        for r4 in conn.execute(
            "SELECT to_id FROM ogs_edge WHERE kind = ? AND from_id = ?",
            ("deploys", rid),
        ):
            eid = str(r4["to_id"])
            env = fetch_entity(conn, eid)
            if env and env.get("kind") == "environment":
                deployments.append(
                    {
                        "release_entity_id": rid,
                        "environment_entity_id": eid,
                        "environment_name": env.get("display_name"),
                        "payload": env.get("payload") or {},
                        "external_ref": env.get("external_ref"),
                    }
                )

    return {
        "ok": True,
        "linked": True,
        "story_id": sid,
        "story_entity_id": story_eid,
        "builds": builds,
        "artifacts": artifacts,
        "releases": releases,
        "deployments": deployments,
    }
