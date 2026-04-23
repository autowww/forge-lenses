"""Story → test_case → defect → release and test_run evidence (orchestration graph)."""

from __future__ import annotations

import sqlite3
from typing import Any

from lenses.orchestration_graph.portfolio import story_entity_index
from lenses.orchestration_graph.query import fetch_entity


def story_quality_trace_from_graph(conn: sqlite3.Connection, wbs_story_id: str) -> dict[str, Any]:
    sid = (wbs_story_id or "").strip()
    if not sid:
        return {"ok": False, "error": "missing_story_id"}

    idx = story_entity_index(conn)
    story_eid = idx.get(sid)
    if not story_eid:
        return {"ok": True, "linked": False, "story_id": sid}

    test_cases: list[dict[str, Any]] = []
    for r in conn.execute(
        "SELECT from_id FROM ogs_edge WHERE kind = ? AND to_id = ?",
        ("validates", story_eid),
    ):
        cid = str(r["from_id"])
        ent = fetch_entity(conn, cid)
        if ent and ent.get("kind") == "test_case":
            test_cases.append(
                {
                    "entity_id": cid,
                    "display_name": ent.get("display_name"),
                    "payload": ent.get("payload") or {},
                    "external_ref": ent.get("external_ref"),
                }
            )

    test_suites: list[dict[str, Any]] = []
    seen_su: set[str] = set()
    for tc in test_cases:
        tid = str(tc["entity_id"])
        for r2 in conn.execute(
            "SELECT from_id FROM ogs_edge WHERE kind = ? AND to_id = ?",
            ("contains", tid),
        ):
            suid = str(r2["from_id"])
            if suid in seen_su:
                continue
            suent = fetch_entity(conn, suid)
            if suent and suent.get("kind") == "test_suite":
                seen_su.add(suid)
                test_suites.append(
                    {
                        "entity_id": suid,
                        "display_name": suent.get("display_name"),
                        "payload": suent.get("payload") or {},
                        "external_ref": suent.get("external_ref"),
                    }
                )

    test_plans: list[dict[str, Any]] = []
    seen_pl: set[str] = set()
    for su in test_suites:
        suid = str(su["entity_id"])
        for r3 in conn.execute(
            "SELECT from_id FROM ogs_edge WHERE kind = ? AND to_id = ?",
            ("contains", suid),
        ):
            pid = str(r3["from_id"])
            if pid in seen_pl:
                continue
            pent = fetch_entity(conn, pid)
            if pent and pent.get("kind") == "test_plan":
                seen_pl.add(pid)
                test_plans.append(
                    {
                        "entity_id": pid,
                        "display_name": pent.get("display_name"),
                        "payload": pent.get("payload") or {},
                        "external_ref": pent.get("external_ref"),
                    }
                )

    test_runs: list[dict[str, Any]] = []
    seen_tr: set[str] = set()
    for r4 in conn.execute(
        "SELECT from_id FROM ogs_edge WHERE kind = ? AND to_id = ?",
        ("tests", story_eid),
    ):
        trid = str(r4["from_id"])
        if trid in seen_tr:
            continue
        trent = fetch_entity(conn, trid)
        if trent and trent.get("kind") == "test_run":
            seen_tr.add(trid)
            test_runs.append(
                {
                    "entity_id": trid,
                    "display_name": trent.get("display_name"),
                    "payload": trent.get("payload") or {},
                    "external_ref": trent.get("external_ref"),
                }
            )

    defects: list[dict[str, Any]] = []
    seen_def: set[str] = set()
    for tc in test_cases:
        tid = str(tc["entity_id"])
        for r5 in conn.execute(
            "SELECT to_id FROM ogs_edge WHERE kind = ? AND from_id = ?",
            ("raised_defect", tid),
        ):
            did = str(r5["to_id"])
            if did in seen_def:
                continue
            dent = fetch_entity(conn, did)
            if dent and dent.get("kind") == "defect":
                seen_def.add(did)
                defects.append(
                    {
                        "entity_id": did,
                        "display_name": dent.get("display_name"),
                        "payload": dent.get("payload") or {},
                        "external_ref": dent.get("external_ref"),
                    }
                )

    releases: list[dict[str, Any]] = []
    seen_rel: set[str] = set()
    for d in defects:
        did = str(d["entity_id"])
        for r6 in conn.execute(
            "SELECT to_id FROM ogs_edge WHERE kind = ? AND from_id = ?",
            ("affects", did),
        ):
            rid = str(r6["to_id"])
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

    return {
        "ok": True,
        "linked": True,
        "story_id": sid,
        "story_entity_id": story_eid,
        "test_plans": test_plans,
        "test_suites": test_suites,
        "test_cases": test_cases,
        "test_runs": test_runs,
        "defects": defects,
        "releases": releases,
    }
