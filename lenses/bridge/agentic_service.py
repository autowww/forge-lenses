"""Sprint B3 agentic bridge — graph entities, runs, approvals, evidence links."""

from __future__ import annotations

import json
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from lenses.bridge.agentic_bridge_registry import load_agentic_bridge_registry
from lenses.bridge.agentic_discovery import build_rules_manifest, discover_forge_config, list_cursor_rules
from lenses.bridge.agentic_drift import compute_agentic_drift
from lenses.bridge.methodology_service import upsert_ogs_entity
from lenses.bridge.trace_service import insert_bridge_link
from lenses.orchestration_graph.query import _row_edge, fetch_entity


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def get_entity_bundle(conn: sqlite3.Connection, entity_id: str) -> dict[str, Any]:
    ent = fetch_entity(conn, entity_id)
    if ent is None:
        return {"ok": False, "error": "entity_not_found"}
    out_e = [_row_edge(r) for r in conn.execute("SELECT * FROM ogs_edge WHERE from_id = ?", (entity_id,))]
    in_e = [_row_edge(r) for r in conn.execute("SELECT * FROM ogs_edge WHERE to_id = ?", (entity_id,))]
    return {"ok": True, "entity": ent, "outgoing_edges": out_e, "incoming_edges": in_e}


def list_registry_tasklets(reg: dict[str, Any]) -> dict[str, Any]:
    t = reg.get("tasklets") or {}
    items = []
    for tid, row in t.items():
        if isinstance(row, dict):
            items.append({"id": tid, **row})
    return {"ok": True, "tasklets": sorted(items, key=lambda x: x["id"])}


def list_registry_recipes(reg: dict[str, Any]) -> dict[str, Any]:
    t = reg.get("recipes") or {}
    items = []
    for tid, row in t.items():
        if isinstance(row, dict):
            items.append({"id": tid, **row})
    return {"ok": True, "recipes": sorted(items, key=lambda x: x["id"])}


def list_registry_policies(reg: dict[str, Any]) -> dict[str, Any]:
    return {"ok": True, "policies": list(reg.get("policy_rules_default") or [])}


def list_graph_by_kind(conn: sqlite3.Connection, kind: str, *, limit: int = 200) -> list[dict[str, Any]]:
    lim = max(1, min(limit, 500))
    rows = conn.execute(
        """
        SELECT id, kind, display_name, summary, payload_json, updated_at
        FROM ogs_entity WHERE kind = ? ORDER BY updated_at DESC LIMIT ?
        """,
        (kind, lim),
    ).fetchall()
    out = []
    for r in rows:
        try:
            p = json.loads(r["payload_json"] or "{}")
        except json.JSONDecodeError:
            p = {}
        out.append(
            {
                "id": r["id"],
                "kind": r["kind"],
                "display_name": r["display_name"],
                "summary": r["summary"] or "",
                "payload": p if isinstance(p, dict) else {},
                "updated_at": r["updated_at"],
            }
        )
    return out


def versonas_payload(workspace_root: Path, conn: sqlite3.Connection) -> dict[str, Any]:
    reg = load_agentic_bridge_registry()
    cfg = discover_forge_config(workspace_root)
    graph_families = list_graph_by_kind(conn, "versona_family", limit=100)
    graph_profiles = list_graph_by_kind(conn, "versona_profile", limit=200)
    return {
        "ok": True,
        "forge_config": {
            "present": cfg.get("present"),
            "ok": cfg.get("ok"),
            "active_versona_families": cfg.get("active_versona_families") or [],
            "active_disciplines": cfg.get("active_disciplines") or [],
        },
        "graph_families": graph_families,
        "graph_profiles": graph_profiles,
        "registry_version": reg.get("registry_version"),
    }


def recipes_payload(workspace_root: Path, conn: sqlite3.Connection) -> dict[str, Any]:
    reg = load_agentic_bridge_registry()
    static = list_registry_recipes(reg)
    globs = list(reg.get("recipe_scan_globs") or [])
    from lenses.bridge.agentic_discovery import discover_recipe_files

    discovered = discover_recipe_files(workspace_root, globs)
    graph_recipes = list_graph_by_kind(conn, "recipe", limit=100)
    return {
        "ok": True,
        "registry_recipes": static.get("recipes") or [],
        "discovered_files": discovered,
        "graph_recipes": graph_recipes,
    }


def tasklets_payload(conn: sqlite3.Connection) -> dict[str, Any]:
    reg = load_agentic_bridge_registry()
    static = list_registry_tasklets(reg)
    graph_tasklets = list_graph_by_kind(conn, "tasklet", limit=200)
    return {
        "ok": True,
        "registry_tasklets": static.get("tasklets") or [],
        "graph_tasklets": graph_tasklets,
    }


def policies_payload(conn: sqlite3.Connection) -> dict[str, Any]:
    reg = load_agentic_bridge_registry()
    base = list_registry_policies(reg)
    graph_pol = list_graph_by_kind(conn, "policy_rule", limit=100)
    return {"ok": True, "registry_policies": base.get("policies") or [], "graph_policies": graph_pol}


def manifests_payload(workspace_root: Path, conn: sqlite3.Connection) -> dict[str, Any]:
    reg = load_agentic_bridge_registry()
    live = build_rules_manifest(workspace_root, reg)
    graph_m = list_graph_by_kind(conn, "rules_manifest", limit=50)
    return {"ok": True, "live_manifest": live, "graph_manifests": graph_m}


def drift_payload(workspace_root: Path) -> dict[str, Any]:
    reg = load_agentic_bridge_registry()
    return {"ok": True, **compute_agentic_drift(workspace_root, reg)}


def create_launch_pack(conn: sqlite3.Connection, body: dict[str, Any]) -> dict[str, Any]:
    title = str(body.get("title") or "Launch pack").strip()
    eid = str(body.get("id") or "").strip() or f"ogs:b3:lp:{uuid.uuid4().hex[:12]}"
    payload = {
        "template_id": str(body.get("template_id") or "default"),
        "owner": str(body.get("owner") or ""),
        "status": str(body.get("status") or "draft"),
        "read_only": bool(body.get("read_only", True)),
        "write_capable": bool(body.get("write_capable", False)),
        "provenance": body.get("provenance") or {},
    }
    upsert_ogs_entity(
        conn,
        entity_id=eid,
        kind="launch_pack",
        display_name=title,
        summary=str(body.get("summary") or "")[:500],
        payload=payload,
        source_system="agentic_b3",
        source_record_id="launch_pack",
    )
    conn.commit()
    return {"ok": True, "id": eid}


def create_agent_run(conn: sqlite3.Connection, body: dict[str, Any]) -> dict[str, Any]:
    mode = str(body.get("execution_mode") or "read_only").strip().lower()
    if mode not in ("read_only", "draft", "write", "approval_gated"):
        return {"ok": False, "error": "invalid_execution_mode"}
    title = str(body.get("title") or f"Agent run ({mode})").strip()
    run_id = str(body.get("id") or "").strip() or f"ogs:b3:run:{uuid.uuid4().hex[:12]}"
    recipe_entity = str(body.get("recipe_entity_id") or "").strip()
    recipe_registry_id = str(body.get("recipe_registry_id") or "").strip()
    target_id = str(body.get("execution_target_id") or "").strip()
    story_id = str(body.get("linked_story_id") or "").strip()

    write_capable = mode in ("write", "approval_gated")
    needs_approval = write_capable

    payload: dict[str, Any] = {
        "execution_mode": mode,
        "read_only": mode == "read_only",
        "write_capable": write_capable,
        "draft_producing": mode == "draft",
        "prompt_pack_version": str(body.get("prompt_pack_version") or "1"),
        "launch_context": body.get("launch_context") if isinstance(body.get("launch_context"), dict) else {},
        "status": "awaiting_approval" if needs_approval else "running",
        "owner": str(body.get("owner") or ""),
        "recipe_registry_id": recipe_registry_id,
        "provenance": {"source": "api", "created_at": _now_iso()},
    }

    upsert_ogs_entity(
        conn,
        entity_id=run_id,
        kind="agent_run",
        display_name=title,
        summary=str(body.get("summary") or mode)[:500],
        payload=payload,
        source_system="agentic_b3",
        source_record_id=mode,
    )

    if recipe_entity:
        insert_bridge_link(
            conn,
            from_id=run_id,
            to_id=recipe_entity,
            kind="executes",
            source_system="agentic_b3",
        )
    if target_id:
        insert_bridge_link(
            conn,
            from_id=run_id,
            to_id=target_id,
            kind="references",
            source_system="agentic_b3",
        )
    if story_id:
        insert_bridge_link(
            conn,
            from_id=run_id,
            to_id=story_id,
            kind="references",
            source_system="agentic_b3",
        )

    approval_id = ""
    if needs_approval:
        approval_id = str(body.get("approval_request_id") or "").strip() or f"ogs:b3:apr:{uuid.uuid4().hex[:10]}"
        ap_payload = {
            "status": "pending",
            "for_run_id": run_id,
            "owner": str(body.get("owner") or ""),
            "requires_human": True,
            "scope": "write_or_gated_run",
        }
        upsert_ogs_entity(
            conn,
            entity_id=approval_id,
            kind="approval_request",
            display_name=f"Approval — {title}"[:200],
            summary="Pending human approval for agent run",
            payload=ap_payload,
            source_system="agentic_b3",
            source_record_id=run_id,
        )
        insert_bridge_link(
            conn,
            from_id=run_id,
            to_id=approval_id,
            kind="seeks_approval",
            source_system="agentic_b3",
        )

    conn.commit()
    return {"ok": True, "id": run_id, "approval_request_id": approval_id or None}


def approve_agent_run(conn: sqlite3.Connection, run_id: str, body: dict[str, Any]) -> dict[str, Any]:
    ent = fetch_entity(conn, run_id)
    if ent is None or str(ent.get("kind")) != "agent_run":
        return {"ok": False, "error": "agent_run_not_found"}
    payload = dict(ent.get("payload") or {}) if isinstance(ent.get("payload"), dict) else {}
    mode = str(payload.get("execution_mode") or "")
    write_capable = bool(payload.get("write_capable"))
    if write_capable and not bool(body.get("confirm_human_approval")):
        return {
            "ok": False,
            "error": "human_approval_required",
            "detail": "Set confirm_human_approval:true for write-capable or gated runs.",
        }
    signed_by = str(body.get("approved_by") or body.get("login") or "unknown").strip() or "unknown"

    # find approval_request via outgoing seeks_approval
    apr_id = None
    for row in conn.execute("SELECT to_id FROM ogs_edge WHERE from_id = ? AND kind = 'seeks_approval'", (run_id,)):
        tid = str(row["to_id"])
        other = fetch_entity(conn, tid)
        if other and str(other.get("kind")) == "approval_request":
            apr_id = tid
            break

    now = _now_iso()
    if apr_id:
        o = fetch_entity(conn, apr_id)
        ap = dict(o.get("payload") or {}) if o and isinstance(o.get("payload"), dict) else {}
        ap["status"] = "approved"
        ap["approved_at"] = now
        ap["approved_by"] = signed_by
        conn.execute(
            "UPDATE ogs_entity SET payload_json = ?, updated_at = ? WHERE id = ?",
            (json.dumps(ap, separators=(",", ":"), sort_keys=True), now, apr_id),
        )

    payload["status"] = "completed_approved"
    payload["approved_at"] = now
    payload["approved_by"] = signed_by
    conn.execute(
        """
        UPDATE ogs_entity SET payload_json = ?, summary = ?, updated_at = ?
        WHERE id = ?
        """,
        (
            json.dumps(payload, separators=(",", ":"), sort_keys=True),
            str(payload.get("execution_mode") or "")[:500],
            now,
            run_id,
        ),
    )
    conn.commit()
    return {"ok": True, "id": run_id, "payload": payload, "approval_request_id": apr_id}


def link_agent_output_to_artifact(conn: sqlite3.Connection, output_id: str, artifact_id: str) -> dict[str, Any]:
    out = fetch_entity(conn, output_id)
    art = fetch_entity(conn, artifact_id)
    if out is None or str(out.get("kind")) != "agent_output":
        return {"ok": False, "error": "agent_output_not_found"}
    if art is None or str(art.get("kind")) not in ("methodology_artifact", "evidence"):
        return {"ok": False, "error": "target_must_be_methodology_artifact_or_evidence"}
    r = insert_bridge_link(
        conn,
        from_id=output_id,
        to_id=artifact_id,
        kind="references",
        source_system="agentic_b3",
    )
    if not r.get("ok"):
        return r
    # annotate output payload
    p = dict(out.get("payload") or {}) if isinstance(out.get("payload"), dict) else {}
    p["linked_evidence_id"] = artifact_id
    now = _now_iso()
    conn.execute(
        "UPDATE ogs_entity SET payload_json = ?, updated_at = ? WHERE id = ?",
        (json.dumps(p, separators=(",", ":"), sort_keys=True), now, output_id),
    )
    conn.commit()
    return {"ok": True, "edge": r, "output_id": output_id}


def list_agent_runs(conn: sqlite3.Connection, *, limit: int = 100) -> dict[str, Any]:
    rows = list_graph_by_kind(conn, "agent_run", limit=limit)
    pending = []
    for r in rows:
        st = (r.get("payload") or {}).get("status")
        if st in ("awaiting_approval", "pending_approval"):
            pending.append(r["id"])
    return {"ok": True, "runs": rows, "pending_approval_run_ids": pending}


def list_pending_approvals(conn: sqlite3.Connection, *, limit: int = 100) -> dict[str, Any]:
    rows = list_graph_by_kind(conn, "approval_request", limit=limit)
    pending = [r for r in rows if (r.get("payload") or {}).get("status") == "pending"]
    return {"ok": True, "approval_requests": pending}
