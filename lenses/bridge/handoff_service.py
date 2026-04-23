"""Sprint B5 — handoff packages, execution sessions, return ingestion, gaps."""

from __future__ import annotations

import hashlib
import json
import sqlite3
import uuid
from datetime import datetime, timezone
from typing import Any

from lenses.bridge.agentic_service import list_graph_by_kind
from lenses.bridge.handoff_renderers import render_all_exports
from lenses.bridge.methodology_service import upsert_ogs_entity
from lenses.bridge.trace_service import insert_bridge_link
from lenses.orchestration_graph.query import fetch_entity


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _row_payload(ent: dict[str, Any] | None) -> dict[str, Any]:
    if not ent or not isinstance(ent.get("payload"), dict):
        return {}
    return dict(ent["payload"])


def _sha256_canonical(obj: Any) -> str:
    raw = json.dumps(obj, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def ensure_handoff_targets(conn: sqlite3.Connection) -> None:
    for key, title in (("cursor", "Handoff target — Cursor"), ("claude", "Handoff target — Claude")):
        eid = f"ogs:b5:target:{key}"
        if fetch_entity(conn, eid):
            continue
        upsert_ogs_entity(
            conn,
            entity_id=eid,
            kind="handoff_target",
            display_name=title,
            summary=f"Export formatting profile: {key}",
            payload={"target_key": key, "vendor_neutral": True},
            source_system="handoff_b5",
            source_record_id=key,
        )
    conn.commit()


def _out_edges(conn: sqlite3.Connection, eid: str) -> list[dict[str, Any]]:
    return [dict(r) for r in conn.execute("SELECT * FROM ogs_edge WHERE from_id = ?", (eid,))]


def _in_edges(conn: sqlite3.Connection, eid: str) -> list[dict[str, Any]]:
    return [dict(r) for r in conn.execute("SELECT * FROM ogs_edge WHERE to_id = ?", (eid,))]


def list_story_entity_ids_for_work_item(conn: sqlite3.Connection, work_item_id: str) -> list[str]:
    """Resolve WBS id (e.g. S-1842) or graph story id to ogs story rows."""
    wid = work_item_id.strip()
    found: list[str] = []
    if wid.startswith("ogs:"):
        ent = fetch_entity(conn, wid)
        if ent and str(ent.get("kind")) in ("story", "task"):
            found.append(wid)
            if str(ent.get("kind")) == "task":
                for e in _in_edges(conn, wid):
                    if e.get("kind") == "contains":
                        p = str(e.get("from_id") or "")
                        pe = fetch_entity(conn, p)
                        if pe and str(pe.get("kind")) == "story":
                            found.append(p)
        return list(dict.fromkeys(found))

    for row in conn.execute(
        "SELECT id, payload_json FROM ogs_entity WHERE kind = 'story'",
    ):
        try:
            p = json.loads(row["payload_json"] or "{}")
        except json.JSONDecodeError:
            p = {}
        if str(p.get("story_id") or "") == wid:
            found.append(str(row["id"]))
    return found


def list_handoff_packages_for_work_item(conn: sqlite3.Connection, work_item_id: str) -> list[str]:
    candidates = list_story_entity_ids_for_work_item(conn, work_item_id)
    if not candidates:
        candidates = [work_item_id.strip()]
    out: list[str] = []
    for cid in candidates:
        for row in conn.execute(
            """
            SELECT e.id FROM ogs_entity e
            JOIN ogs_edge ex ON ex.from_id = e.id AND ex.kind = 'scopes_handoff' AND ex.to_id = ?
            WHERE e.kind = 'handoff_package'
            """,
            (cid,),
        ):
            out.append(str(row["id"]))
    return list(dict.fromkeys(out))


def get_handoff_bundle(conn: sqlite3.Connection, package_id: str) -> dict[str, Any]:
    ent = fetch_entity(conn, package_id)
    if ent is None or str(ent.get("kind")) != "handoff_package":
        return {"ok": False, "error": "handoff_package_not_found"}
    out_e = [dict(r) for r in conn.execute("SELECT * FROM ogs_edge WHERE from_id = ?", (package_id,))]
    in_e = [dict(r) for r in conn.execute("SELECT * FROM ogs_edge WHERE to_id = ?", (package_id,))]
    children: list[dict[str, Any]] = []
    for e in out_e:
        if e.get("kind") == "contains":
            ch = fetch_entity(conn, str(e.get("to_id") or ""))
            if ch:
                children.append(ch)
    return {"ok": True, "package": ent, "outgoing_edges": out_e, "incoming_edges": in_e, "children": children}


def _gather_export_fields(conn: sqlite3.Connection, package_id: str) -> dict[str, Any] | None:
    b = get_handoff_bundle(conn, package_id)
    if not b.get("ok"):
        return None
    p = _row_payload(b["package"])
    wu: list[str] = []
    arts: list[str] = []
    recipes: list[str] = []
    lp_ver = str(p.get("launch_pack_version") or "")
    lp_entity = ""
    for e in b["outgoing_edges"]:
        tid = str(e.get("to_id") or "")
        if e.get("kind") == "scopes_handoff":
            wu.append(tid)
        elif e.get("kind") == "references":
            o = fetch_entity(conn, tid)
            if not o:
                continue
            k = str(o.get("kind"))
            if k == "methodology_artifact":
                arts.append(f"{o.get('display_name')} ({tid})")
            elif k == "evidence":
                arts.append(f"evidence:{tid}")
            elif k == "decision_record":
                arts.append(f"decision:{tid}")
            elif k == "recipe":
                recipes.append(str(o.get("display_name") or tid))
            elif k == "launch_pack":
                lp_entity = tid
                lp = _row_payload(o)
                lp_ver = str(lp.get("template_id") or lp_ver or "embedded")
    target_key = str(p.get("target_key") or "cursor")
    oc = p.get("output_contract")
    if not isinstance(oc, (dict, str)):
        oc = {}
    tasklets = list(p.get("tasklets") or []) if isinstance(p.get("tasklets"), list) else []
    return {
        "title": str(b["package"].get("display_name") or "Handoff"),
        "objective": str(p.get("objective") or ""),
        "work_unit_ids": wu,
        "acceptance_criteria": list(p.get("acceptance_criteria") or []) if isinstance(p.get("acceptance_criteria"), list) else [],
        "scope_boundaries": list(p.get("scope_boundaries") or []) if isinstance(p.get("scope_boundaries"), list) else [],
        "files_of_interest": list(p.get("files_of_interest") or []) if isinstance(p.get("files_of_interest"), list) else [],
        "recipes": recipes,
        "tasklets": [str(x) for x in tasklets],
        "gate_expectations": list(p.get("gate_expectations") or []) if isinstance(p.get("gate_expectations"), list) else [],
        "output_contract": oc,
        "artifact_lines": arts,
        "launch_pack_version": lp_ver,
        "launch_pack_entity_id": lp_entity,
        "target_key": target_key,
    }


def export_handoff(conn: sqlite3.Connection, package_id: str, body: dict[str, Any]) -> dict[str, Any]:
    fields = _gather_export_fields(conn, package_id)
    if fields is None:
        return {"ok": False, "error": "handoff_package_not_found"}
    target_key = str(body.get("target_key") or fields["target_key"])
    exports = render_all_exports(
        target_key=target_key,
        title=fields["title"],
        objective=fields["objective"],
        work_unit_ids=fields["work_unit_ids"],
        acceptance_criteria=[str(x) for x in fields["acceptance_criteria"]],
        scope_boundaries=[str(x) for x in fields["scope_boundaries"]],
        files_of_interest=[str(x) for x in fields["files_of_interest"]],
        recipes=fields["recipes"],
        tasklets=[str(x) for x in fields["tasklets"]],
        gate_expectations=[str(x) for x in fields["gate_expectations"]],
        output_contract=fields["output_contract"],
        artifact_lines=fields["artifact_lines"],
        launch_pack_version=fields["launch_pack_version"],
    )
    want = body.get("formats")
    if isinstance(want, list) and want:
        exports = {k: v for k, v in exports.items() if k in {str(x) for x in want}}
    return {"ok": True, "package_id": package_id, "target_key": target_key, "exports": exports}


def create_handoff_package(conn: sqlite3.Connection, body: dict[str, Any]) -> dict[str, Any]:
    ensure_handoff_targets(conn)
    target_key = str(body.get("target_key") or "cursor").strip().lower()
    if target_key not in ("cursor", "claude"):
        return {"ok": False, "error": "invalid_target_key"}

    title = str(body.get("title") or "Handoff package").strip()[:200]
    pkg_id = str(body.get("id") or "").strip() or f"ogs:b5:pkg:{uuid.uuid4().hex[:12]}"
    lp_ver = str(body.get("launch_pack_version") or body.get("launch_pack_template_id") or "1")

    payload: dict[str, Any] = {
        "objective": str(body.get("objective") or ""),
        "acceptance_criteria": body.get("acceptance_criteria") if isinstance(body.get("acceptance_criteria"), list) else [],
        "scope_boundaries": body.get("scope_boundaries") if isinstance(body.get("scope_boundaries"), list) else [],
        "files_of_interest": body.get("files_of_interest") if isinstance(body.get("files_of_interest"), list) else [],
        "tasklets": body.get("tasklets") if isinstance(body.get("tasklets"), list) else [],
        "gate_expectations": body.get("gate_expectations") if isinstance(body.get("gate_expectations"), list) else [],
        "output_contract": body.get("output_contract") if isinstance(body.get("output_contract"), (dict, str)) else {},
        "target_key": target_key,
        "launch_pack_version": lp_ver,
        "status": "drafted",
        "approval_status": str(body.get("approval_status") or "pending"),
        "return_status": "none",
        "created_at": _now_iso(),
    }

    upsert_ogs_entity(
        conn,
        entity_id=pkg_id,
        kind="handoff_package",
        display_name=title,
        summary=str(payload["objective"])[:500],
        payload=payload,
        source_system="handoff_b5",
        source_record_id=target_key,
    )

    pb = f"ogs:b5:pb:{uuid.uuid4().hex[:10]}"
    cb = f"ogs:b5:cb:{uuid.uuid4().hex[:10]}"
    upsert_ogs_entity(
        conn,
        entity_id=pb,
        kind="prompt_bundle",
        display_name=f"Prompt bundle — {title}"[:200],
        summary="Structured prompts for handoff",
        payload={"format": "markdown", "preview": str(body.get("prompt_preview") or "")[:2000]},
        source_system="handoff_b5",
        source_record_id=pkg_id,
    )
    upsert_ogs_entity(
        conn,
        entity_id=cb,
        kind="context_bundle",
        display_name=f"Context bundle — {title}"[:200],
        summary="Files, graph ids, constraints",
        payload={"graph_context": body.get("graph_context") if isinstance(body.get("graph_context"), dict) else {}},
        source_system="handoff_b5",
        source_record_id=pkg_id,
    )

    tgt = f"ogs:b5:target:{target_key}"
    for fn, tn, k in (
        (pkg_id, pb, "contains"),
        (pkg_id, cb, "contains"),
        (pkg_id, tgt, "references"),
    ):
        r = insert_bridge_link(conn, from_id=fn, to_id=tn, kind=k, source_system="handoff_b5")
        if not r.get("ok"):
            return r

    for wid in body.get("work_unit_graph_ids") or []:
        w = str(wid).strip()
        if w and fetch_entity(conn, w):
            insert_bridge_link(
                conn,
                from_id=pkg_id,
                to_id=w,
                kind="scopes_handoff",
                source_system="handoff_b5",
            )

    for lk in body.get("artifact_graph_ids") or []:
        x = str(lk).strip()
        if x and fetch_entity(conn, x):
            insert_bridge_link(conn, from_id=pkg_id, to_id=x, kind="references", source_system="handoff_b5")

    lp = str(body.get("launch_pack_entity_id") or "").strip()
    if lp and fetch_entity(conn, lp):
        insert_bridge_link(conn, from_id=pkg_id, to_id=lp, kind="references", source_system="handoff_b5")

    for rid in body.get("recipe_entity_ids") or []:
        r = str(rid).strip()
        if r and fetch_entity(conn, r):
            insert_bridge_link(conn, from_id=pkg_id, to_id=r, kind="references", source_system="handoff_b5")

    conn.commit()
    return {"ok": True, "id": pkg_id, "prompt_bundle_id": pb, "context_bundle_id": cb}


def _session_for_package(conn: sqlite3.Connection, package_id: str) -> list[str]:
    rows = conn.execute(
        "SELECT from_id FROM ogs_edge WHERE to_id = ? AND kind = 'session_for'",
        (package_id,),
    ).fetchall()
    return [str(r[0]) for r in rows]


def _returns_for_session(conn: sqlite3.Connection, session_id: str) -> list[dict[str, Any]]:
    ids = [
        str(r[0])
        for r in conn.execute(
            "SELECT from_id FROM ogs_edge WHERE to_id = ? AND kind = 'derived_from'",
            (session_id,),
        ).fetchall()
    ]
    return [fetch_entity(conn, i) for i in ids if fetch_entity(conn, i)]


def get_or_create_execution_session(conn: sqlite3.Connection, package_id: str, body: dict[str, Any]) -> str:
    sid = str(body.get("execution_session_id") or "").strip()
    if sid and fetch_entity(conn, sid):
        return sid
    existing = _session_for_package(conn, package_id)
    if existing and not body.get("force_new_session"):
        return existing[0]
    sid = str(body.get("new_session_id") or "").strip() or f"ogs:b5:sess:{uuid.uuid4().hex[:12]}"
    upsert_ogs_entity(
        conn,
        entity_id=sid,
        kind="execution_session",
        display_name=str(body.get("session_title") or f"Session — {package_id[:24]}")[:200],
        summary="Agent-assisted execution session",
        payload={
            "handoff_package_id": package_id,
            "target_key": str(body.get("target_key") or ""),
            "started_at": _now_iso(),
            "status": "active",
        },
        source_system="handoff_b5",
        source_record_id=package_id,
    )
    insert_bridge_link(conn, from_id=sid, to_id=package_id, kind="session_for", source_system="handoff_b5")
    conn.commit()
    return sid


def ingest_return(conn: sqlite3.Connection, package_id: str, body: dict[str, Any]) -> dict[str, Any]:
    pkg = fetch_entity(conn, package_id)
    if pkg is None or str(pkg.get("kind")) != "handoff_package":
        return {"ok": False, "error": "handoff_package_not_found"}

    fingerprint = str(body.get("ingest_fingerprint") or "").strip() or _sha256_canonical(body)
    session_id = get_or_create_execution_session(conn, package_id, body)

    for prev in _returns_for_session(conn, session_id):
        pp = _row_payload(prev)
        if str(pp.get("ingest_fingerprint") or "") == fingerprint:
            return {"ok": True, "duplicate": True, "execution_return_id": str(prev.get("id")), "session_id": session_id}

    rid = str(body.get("execution_return_id") or "").strip() or f"ogs:b5:ret:{uuid.uuid4().hex[:12]}"
    now = _now_iso()
    partial = bool(body.get("partial_return", False))
    ret_payload: dict[str, Any] = {
        "ingest_fingerprint": fingerprint,
        "ingested_at": now,
        "branch_name": str(body.get("branch_name") or ""),
        "pr_number": body.get("pr_number"),
        "pr_url": str(body.get("pr_url") or ""),
        "changed_files": list(body.get("changed_files") or []) if isinstance(body.get("changed_files"), list) else [],
        "test_summary": body.get("test_summary") if isinstance(body.get("test_summary"), dict) else {},
        "blockers": list(body.get("blockers") or []) if isinstance(body.get("blockers"), list) else [],
        "review_state": str(body.get("review_state") or ""),
        "satisfied_acceptance_keys": list(body.get("satisfied_acceptance_keys") or [])
        if isinstance(body.get("satisfied_acceptance_keys"), list)
        else [],
        "partial_return": partial,
        "stale": bool(body.get("mark_stale", False)),
        "provenance": body.get("provenance") if isinstance(body.get("provenance"), dict) else {"source": "api"},
    }

    upsert_ogs_entity(
        conn,
        entity_id=rid,
        kind="execution_return",
        display_name=str(body.get("return_title") or "Execution return")[:200],
        summary=str(ret_payload.get("branch_name") or ret_payload.get("pr_url") or "return")[:500],
        payload=ret_payload,
        source_system="handoff_b5",
        source_record_id=session_id,
    )
    insert_bridge_link(conn, from_id=rid, to_id=session_id, kind="derived_from", source_system="handoff_b5")

    mid = f"ogs:b5:om:{uuid.uuid4().hex[:10]}"
    upsert_ogs_entity(
        conn,
        entity_id=mid,
        kind="output_manifest",
        display_name="Output manifest",
        summary="Files and artifacts from return",
        payload={"items": list(body.get("manifest_items") or [])},
        source_system="handoff_b5",
        source_record_id=rid,
    )
    insert_bridge_link(conn, from_id=rid, to_id=mid, kind="contains", source_system="handoff_b5")

    for i, rel in enumerate(ret_payload["changed_files"][:50]):
        if not isinstance(rel, str) or not rel.strip():
            continue
        fid = f"ogs:b5:fc:{uuid.uuid4().hex[:10]}"
        upsert_ogs_entity(
            conn,
            entity_id=fid,
            kind="file_change_summary",
            display_name=rel.split("/")[-1][:120],
            summary=rel[:500],
            payload={"path": rel, "change_kind": "modified"},
            source_system="handoff_b5",
            source_record_id=str(i),
        )
        insert_bridge_link(conn, from_id=mid, to_id=fid, kind="contains", source_system="handoff_b5")

    bt = f"ogs:b5:btr:{uuid.uuid4().hex[:10]}"
    upsert_ogs_entity(
        conn,
        entity_id=bt,
        kind="build_test_return",
        display_name="Build / test return",
        summary="Linked CI outcomes",
        payload={"test_summary": ret_payload.get("test_summary"), "notes": str(body.get("build_notes") or "")},
        source_system="handoff_b5",
        source_record_id=rid,
    )
    insert_bridge_link(conn, from_id=rid, to_id=bt, kind="contains", source_system="handoff_b5")
    be = str(body.get("build_entity_id") or "").strip()
    if be and fetch_entity(conn, be):
        insert_bridge_link(conn, from_id=bt, to_id=be, kind="references", source_system="handoff_b5")
    te = str(body.get("test_run_entity_id") or "").strip()
    if te and fetch_entity(conn, te):
        insert_bridge_link(conn, from_id=bt, to_id=te, kind="references", source_system="handoff_b5")

    cr_ref = str(body.get("change_request_entity_id") or "").strip()
    if cr_ref and fetch_entity(conn, cr_ref):
        cref_id = f"ogs:b5:crref:{uuid.uuid4().hex[:10]}"
        upsert_ogs_entity(
            conn,
            entity_id=cref_id,
            kind="code_review_ref",
            display_name=f"PR/MR {body.get('pr_number') or ''}",
            summary=ret_payload.get("review_state") or "review",
            payload={"pr_url": ret_payload.get("pr_url"), "state": ret_payload.get("review_state")},
            source_system="handoff_b5",
            source_record_id=rid,
        )
        insert_bridge_link(conn, from_id=rid, to_id=cref_id, kind="contains", source_system="handoff_b5")
        insert_bridge_link(conn, from_id=cref_id, to_id=cr_ref, kind="references", source_system="handoff_b5")

    ck = f"ogs:b5:ck:{uuid.uuid4().hex[:10]}"
    upsert_ogs_entity(
        conn,
        entity_id=ck,
        kind="sync_checkpoint",
        display_name="Sync checkpoint",
        summary="Idempotent ingest checkpoint",
        payload={"fingerprint": fingerprint, "recorded_at": now},
        source_system="handoff_b5",
        source_record_id=rid,
    )
    insert_bridge_link(conn, from_id=rid, to_id=ck, kind="contains", source_system="handoff_b5")

    rp = str(body.get("review_pack_entity_id") or "").strip()
    if rp and fetch_entity(conn, rp):
        insert_bridge_link(conn, from_id=rid, to_id=rp, kind="references", source_system="handoff_b5")

    pp = _row_payload(pkg)
    pp["return_status"] = "partial" if partial else "received"
    pp["last_return_at"] = now
    pp["last_return_fingerprint"] = fingerprint
    pp["last_execution_session_id"] = session_id
    if partial or ret_payload.get("stale"):
        pp["return_incomplete"] = True
    else:
        pp["return_incomplete"] = False
    conn.execute(
        "UPDATE ogs_entity SET payload_json = ?, updated_at = ? WHERE id = ?",
        (json.dumps(pp, separators=(",", ":"), sort_keys=True), now, package_id),
    )
    conn.commit()
    return {"ok": True, "execution_return_id": rid, "session_id": session_id, "duplicate": False}


def handoff_gaps(conn: sqlite3.Connection, package_id: str) -> dict[str, Any]:
    pkg = fetch_entity(conn, package_id)
    if pkg is None or str(pkg.get("kind")) != "handoff_package":
        return {"ok": False, "error": "handoff_package_not_found"}
    p = _row_payload(pkg)
    criteria = [str(x) for x in (p.get("acceptance_criteria") or [])] if isinstance(p.get("acceptance_criteria"), list) else []
    satisfied: set[str] = set()
    has_review_pack = False
    for sid in _session_for_package(conn, package_id):
        for ent in _returns_for_session(conn, sid):
            rp = _row_payload(ent)
            for x in rp.get("satisfied_acceptance_keys") or []:
                satisfied.add(str(x))
            for e in _out_edges(conn, str(ent.get("id") or "")):
                if e.get("kind") != "references":
                    continue
                t = fetch_entity(conn, str(e.get("to_id") or ""))
                if t and str(t.get("kind")) == "review_pack":
                    has_review_pack = True
    missing_ac = [c for c in criteria if c not in satisfied]
    missing_evidence: list[str] = []
    if not has_review_pack:
        missing_evidence.append("review_pack_link")
    if p.get("return_incomplete"):
        missing_evidence.append("complete_return_or_assay_evidence")
    return {
        "ok": True,
        "package_id": package_id,
        "missing_acceptance": missing_ac,
        "missing_evidence": missing_evidence,
        "approval_status": p.get("approval_status"),
        "return_status": p.get("return_status"),
        "return_incomplete": bool(p.get("return_incomplete")),
    }


def handoff_status(conn: sqlite3.Connection, package_id: str) -> dict[str, Any]:
    b = get_handoff_bundle(conn, package_id)
    if not b.get("ok"):
        return b
    p = _row_payload(b["package"])
    sessions = _session_for_package(conn, package_id)
    latest_return = None
    for sid in sessions:
        for ent in _returns_for_session(conn, sid):
            latest_return = ent
    lr_payload = _row_payload(latest_return)
    return {
        "ok": True,
        "package_id": package_id,
        "status": p.get("status"),
        "approval_status": p.get("approval_status"),
        "return_status": p.get("return_status"),
        "launch_pack_version": p.get("launch_pack_version"),
        "target_key": p.get("target_key"),
        "session_ids": sessions,
        "latest_execution_return": latest_return,
        "branch": lr_payload.get("branch_name"),
        "pr_url": lr_payload.get("pr_url"),
        "partial_return": lr_payload.get("partial_return"),
        "stale": lr_payload.get("stale"),
    }


def execution_session_bundle(conn: sqlite3.Connection, session_id: str) -> dict[str, Any]:
    ent = fetch_entity(conn, session_id)
    if ent is None or str(ent.get("kind")) != "execution_session":
        return {"ok": False, "error": "execution_session_not_found"}
    pkg_id = ""
    for e in _out_edges(conn, session_id):
        if e.get("kind") == "session_for":
            pkg_id = str(e.get("to_id") or "")
            break
    returns = _returns_for_session(conn, session_id)
    return {"ok": True, "session": ent, "handoff_package_id": pkg_id, "returns": [r for r in returns if r]}


def reconcile_execution_session(conn: sqlite3.Connection, session_id: str, body: dict[str, Any]) -> dict[str, Any]:
    ent = fetch_entity(conn, session_id)
    if ent is None or str(ent.get("kind")) != "execution_session":
        return {"ok": False, "error": "execution_session_not_found"}
    p = _row_payload(ent)
    if isinstance(body.get("session_patch"), dict):
        p.update(body["session_patch"])
    now = _now_iso()
    conn.execute(
        "UPDATE ogs_entity SET payload_json = ?, updated_at = ? WHERE id = ?",
        (json.dumps(p, separators=(",", ":"), sort_keys=True), now, session_id),
    )
    rid = str(body.get("patch_return_id") or "").strip()
    if rid:
        r = fetch_entity(conn, rid)
        if r and str(r.get("kind")) == "execution_return":
            rp = _row_payload(r)
            if isinstance(body.get("return_patch"), dict):
                rp.update(body["return_patch"])
            conn.execute(
                "UPDATE ogs_entity SET payload_json = ?, updated_at = ? WHERE id = ?",
                (json.dumps(rp, separators=(",", ":"), sort_keys=True), now, rid),
            )
    conn.commit()
    return {"ok": True, "session_id": session_id}


def handoff_summary_for_work_item(conn: sqlite3.Connection, work_item_id: str) -> dict[str, Any] | None:
    pids = list_handoff_packages_for_work_item(conn, work_item_id)
    if not pids:
        return None
    rows = []
    for pid in pids[:5]:
        st = handoff_status(conn, pid)
        gp = handoff_gaps(conn, pid)
        if st.get("ok"):
            rows.append(
                {
                    "package_id": pid,
                    "status": st,
                    "gaps": gp if gp.get("ok") else {},
                }
            )
    return {"handoff_packages": rows}


def list_handoff_packages(conn: sqlite3.Connection, *, limit: int = 50) -> dict[str, Any]:
    rows = list_graph_by_kind(conn, "handoff_package", limit=limit)
    return {"ok": True, "packages": rows}
