"""Resolve story / task work items to branch, PR/MR, and commits via the orchestration graph."""

from __future__ import annotations

import sqlite3
from typing import Any

from lenses.orchestration_graph.portfolio import story_entity_index
from lenses.orchestration_graph.query import fetch_entity


def story_code_links_from_graph(conn: sqlite3.Connection, wbs_story_id: str) -> dict[str, Any]:
    """Use ``implements``, ``contains``, and ``targets`` edges from the demo / imported graph."""
    sid = (wbs_story_id or "").strip()
    if not sid:
        return {"ok": False, "error": "missing_story_id"}

    idx = story_entity_index(conn)
    story_eid = idx.get(sid)
    if not story_eid:
        return {"ok": True, "linked": False, "story_id": sid}

    change_requests: list[dict[str, Any]] = []
    branches: list[dict[str, Any]] = []
    commits: list[dict[str, Any]] = []

    for r in conn.execute(
        "SELECT from_id FROM ogs_edge WHERE kind = ? AND to_id = ?",
        ("implements", story_eid),
    ):
        cr_id = str(r["from_id"])
        ent = fetch_entity(conn, cr_id)
        if not ent or ent.get("kind") != "change_request":
            continue
        p = ent.get("payload") or {}
        num = p.get("number")
        vcs = str(p.get("vcs") or "github")
        state = str(p.get("state") or "")
        ext = str(ent.get("external_ref") or "")
        url = ""
        if vcs == "github" and ext.startswith("github:pr:"):
            parts = ext.split(":")
            if len(parts) >= 5:
                url = f"https://github.com/{parts[2]}/{parts[3]}/pull/{parts[4]}"
        change_requests.append(
            {
                "entity_id": cr_id,
                "display_name": ent.get("display_name"),
                "number": int(num) if isinstance(num, int) else num,
                "vcs": vcs,
                "state": state,
                "external_ref": ext,
                "url": url or None,
            }
        )

    task_ids: list[str] = []
    for r in conn.execute(
        "SELECT to_id FROM ogs_edge WHERE kind = ? AND from_id = ?",
        ("contains", story_eid),
    ):
        tid = str(r["to_id"])
        trow = conn.execute("SELECT kind FROM ogs_entity WHERE id = ?", (tid,)).fetchone()
        if trow and str(trow["kind"]) == "task":
            task_ids.append(tid)

    for tid in task_ids:
        for r in conn.execute(
            "SELECT to_id FROM ogs_edge WHERE kind = ? AND from_id = ?",
            ("targets", tid),
        ):
            bid = str(r["to_id"])
            bent = fetch_entity(conn, bid)
            if bent and bent.get("kind") == "branch":
                branches.append(
                    {
                        "entity_id": bid,
                        "display_name": bent.get("display_name"),
                        "ref": (bent.get("payload") or {}).get("ref"),
                    }
                )

    seen_commit: set[str] = set()
    for cr in change_requests:
        eid = str(cr["entity_id"])
        for r in conn.execute(
            "SELECT to_id FROM ogs_edge WHERE kind = ? AND from_id = ?",
            ("contains", eid),
        ):
            cid = str(r["to_id"])
            if cid in seen_commit:
                continue
            cent = fetch_entity(conn, cid)
            if cent and cent.get("kind") == "commit":
                seen_commit.add(cid)
                cp = cent.get("payload") or {}
                commits.append(
                    {
                        "entity_id": cid,
                        "short_sha": str(cp.get("short_sha") or ""),
                        "display_name": cent.get("display_name"),
                        "external_ref": cent.get("external_ref"),
                    }
                )

    merge_readiness = "unknown"
    if change_requests:
        st = str(change_requests[0].get("state") or "").lower()
        if st == "merged":
            merge_readiness = "merged"
        elif st == "open":
            merge_readiness = "open"
        else:
            merge_readiness = st

    return {
        "ok": True,
        "linked": True,
        "story_id": sid,
        "story_entity_id": story_eid,
        "change_requests": change_requests,
        "branches": branches,
        "commits": commits,
        "merge_readiness": merge_readiness,
    }
