"""Sprint B4 ceremony bridge — instances, outputs, sign-off, readiness, delivery-mode rules."""

from __future__ import annotations

import json
import sqlite3
import uuid
from datetime import datetime, timezone
from typing import Any

from lenses.bridge.agentic_service import list_graph_by_kind
from lenses.bridge.ceremony_bridge_registry import (
    load_ceremony_bridge_registry,
    merged_ceremony_intents_payload,
)
from lenses.bridge.methodology_service import upsert_ogs_entity
from lenses.bridge.trace_service import insert_bridge_link
from lenses.orchestration_graph.query import fetch_entity


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _row_payload(ent: dict[str, Any] | None) -> dict[str, Any]:
    if not ent or not isinstance(ent.get("payload"), dict):
        return {}
    return dict(ent["payload"])


def delivery_mode_rules(reg: dict[str, Any], mode: str) -> dict[str, Any] | None:
    dm = reg.get("delivery_modes") or {}
    if not isinstance(dm, dict):
        return None
    row = dm.get(mode)
    return row if isinstance(row, dict) else None


def binding_output_types(reg: dict[str, Any]) -> set[str]:
    raw = reg.get("binding_output_types") or []
    if not isinstance(raw, list):
        return set()
    return {str(x) for x in raw if isinstance(x, str)}


def is_binding_output_type(reg: dict[str, Any], output_type: str) -> bool:
    return output_type.strip() in binding_output_types(reg)


def registry_mapping_by_id(reg: dict[str, Any], mid: str) -> dict[str, Any] | None:
    for m in reg.get("mappings") or []:
        if isinstance(m, dict) and str(m.get("id") or "") == mid:
            return m
    return None


def registry_template_by_id(reg: dict[str, Any], tid: str) -> dict[str, Any] | None:
    for t in reg.get("templates") or []:
        if isinstance(t, dict) and str(t.get("id") or "") == tid:
            return t
    return None


def intents_payload() -> dict[str, Any]:
    base = merged_ceremony_intents_payload()
    reg = load_ceremony_bridge_registry()
    return {"ok": True, "delivery_modes": reg.get("delivery_modes"), **base}


def mappings_payload() -> dict[str, Any]:
    reg = load_ceremony_bridge_registry()
    return {"ok": True, "mappings": list(reg.get("mappings") or []), "registry_version": reg.get("registry_version")}


def templates_payload(conn: sqlite3.Connection) -> dict[str, Any]:
    reg = load_ceremony_bridge_registry()
    graph_rows = list_graph_by_kind(conn, "ceremony_template", limit=200)
    static = list(reg.get("templates") or [])
    return {
        "ok": True,
        "registry_templates": static,
        "graph_templates": graph_rows,
        "registry_version": reg.get("registry_version"),
    }


def list_ceremony_instances(conn: sqlite3.Connection, *, limit: int = 100) -> dict[str, Any]:
    rows = list_graph_by_kind(conn, "ceremony_instance", limit=limit)
    return {"ok": True, "instances": rows}


def _out_neighbors(conn: sqlite3.Connection, eid: str) -> list[dict[str, Any]]:
    out = []
    for row in conn.execute("SELECT * FROM ogs_edge WHERE from_id = ?", (eid,)):
        out.append(dict(row))
    return out


def _in_neighbors(conn: sqlite3.Connection, eid: str) -> list[dict[str, Any]]:
    out = []
    for row in conn.execute("SELECT * FROM ogs_edge WHERE to_id = ?", (eid,)):
        out.append(dict(row))
    return out


def _template_for_instance(conn: sqlite3.Connection, instance_id: str) -> dict[str, Any] | None:
    for e in _out_neighbors(conn, instance_id):
        if e.get("kind") == "instantiates":
            tid = str(e.get("to_id") or "")
            if tid:
                return fetch_entity(conn, tid)
    return None


def _intent_entity_for_template(conn: sqlite3.Connection, template_id: str) -> dict[str, Any] | None:
    for e in _out_neighbors(conn, template_id):
        if e.get("kind") == "realizes_intent":
            iid = str(e.get("to_id") or "")
            if iid:
                return fetch_entity(conn, iid)
    return None


def _mapping_entity_for_template(conn: sqlite3.Connection, template_id: str) -> dict[str, Any] | None:
    for e in _out_neighbors(conn, template_id):
        if e.get("kind") == "references":
            mid = str(e.get("to_id") or "")
            if not mid:
                continue
            ent = fetch_entity(conn, mid)
            if ent and str(ent.get("kind")) == "ceremony_mapping":
                return ent
    return None


def _outputs_for_instance(conn: sqlite3.Connection, instance_id: str) -> list[dict[str, Any]]:
    outs = []
    for e in _out_neighbors(conn, instance_id):
        if e.get("kind") != "yields_output":
            continue
        oid = str(e.get("to_id") or "")
        o = fetch_entity(conn, oid)
        if o:
            outs.append(o)
    return outs


def _signoffs_for_instance(conn: sqlite3.Connection, instance_id: str) -> list[dict[str, Any]]:
    found = []
    for e in _in_neighbors(conn, instance_id):
        if e.get("kind") != "approves":
            continue
        sid = str(e.get("from_id") or "")
        s = fetch_entity(conn, sid)
        if s and str(s.get("kind")) == "signoff_record":
            found.append(s)
    return found


def _followups_for_instance(conn: sqlite3.Connection, instance_id: str) -> list[dict[str, Any]]:
    found = []
    for e in _out_neighbors(conn, instance_id):
        if e.get("kind") != "follows_up_with":
            continue
        fid = str(e.get("to_id") or "")
        f = fetch_entity(conn, fid)
        if f:
            found.append(f)
    return found


def _instance_has_human_signoff(conn: sqlite3.Connection, instance_id: str) -> bool:
    for s in _signoffs_for_instance(conn, instance_id):
        p = _row_payload(s)
        if p.get("state") == "signed" and (p.get("signed_by") or "").strip():
            return True
    return False


def _resolve_registry_template(conn: sqlite3.Connection, template_ent: dict[str, Any]) -> dict[str, Any] | None:
    reg = load_ceremony_bridge_registry()
    tp = _row_payload(template_ent)
    rid = str(tp.get("registry_template_id") or "").strip()
    if rid:
        rt = registry_template_by_id(reg, rid)
        if rt:
            return rt
    return None


def validate_projection_label(
    *,
    methodology: str,
    intent_id: str,
    label: str,
    mapping_id: str,
) -> dict[str, Any]:
    reg = load_ceremony_bridge_registry()
    m = registry_mapping_by_id(reg, mapping_id)
    if m is None:
        return {"ok": False, "error": "unknown_mapping", "mapping_id": mapping_id}
    if str(m.get("intent_id") or "") != intent_id:
        return {"ok": False, "error": "mapping_intent_mismatch", "detail": "Mapping does not match ceremony intent."}
    if methodology == "forge":
        expected = str(m.get("forge_ritual") or "").strip()
        if label.strip() != expected:
            return {
                "ok": False,
                "error": "forge_label_not_mapped",
                "expected_forge_ritual": expected,
                "detail": "Ceremony Forge label must match an explicit mapping; arbitrary labels are rejected.",
            }
    return {"ok": True}


def create_ceremony_instance(conn: sqlite3.Connection, body: dict[str, Any]) -> dict[str, Any]:
    reg = load_ceremony_bridge_registry()
    template_id = str(body.get("template_id") or "").strip()
    if not template_id:
        return {"ok": False, "error": "template_id_required"}
    tpl = fetch_entity(conn, template_id)
    if tpl is None or str(tpl.get("kind")) != "ceremony_template":
        return {"ok": False, "error": "ceremony_template_not_found"}

    tp = _row_payload(tpl)
    intent_id = str(tp.get("intent_id") or "").strip()
    if not intent_id:
        return {"ok": False, "error": "template_missing_intent_id"}

    mapping_id = str(body.get("mapping_id") or tp.get("registry_mapping_id") or "").strip()
    if not mapping_id:
        return {"ok": False, "error": "mapping_id_required"}
    m = registry_mapping_by_id(reg, mapping_id)
    if m is None:
        return {"ok": False, "error": "unknown_mapping"}
    if str(m.get("intent_id") or "") != intent_id:
        return {"ok": False, "error": "mapping_intent_mismatch"}

    methodology = str(body.get("methodology") or "forge").strip() or "forge"
    forge_label = str(body.get("forge_projection_label") or m.get("forge_ritual") or "").strip()
    v = validate_projection_label(methodology=methodology, intent_id=intent_id, label=forge_label, mapping_id=mapping_id)
    if not v.get("ok"):
        return v

    mode = str(body.get("delivery_mode") or "").strip()
    if not mode:
        return {"ok": False, "error": "delivery_mode_required"}
    if delivery_mode_rules(reg, mode) is None:
        return {"ok": False, "error": "invalid_delivery_mode"}

    rt = _resolve_registry_template(conn, tpl)
    allowed = tp.get("delivery_modes_allowed")
    if not isinstance(allowed, list) and rt:
        allowed = rt.get("delivery_modes_allowed")
    if isinstance(allowed, list) and mode not in {str(x) for x in allowed}:
        return {"ok": False, "error": "delivery_mode_not_allowed_for_template", "allowed": allowed}

    dm_entity = str(body.get("delivery_mode_entity_id") or "").strip() or f"ogs:demo:b4:dm:{mode}"
    dm_ent = fetch_entity(conn, dm_entity)
    if dm_ent is None or str(dm_ent.get("kind")) != "delivery_mode":
        return {"ok": False, "error": "delivery_mode_entity_not_found", "hint": dm_entity}

    recurrence = str(body.get("recurrence") or tp.get("recurrence") or "one_time").strip()
    inputs = body.get("inputs") if isinstance(body.get("inputs"), dict) else {}

    iid = str(body.get("id") or "").strip() or f"ogs:b4:inst:{uuid.uuid4().hex[:12]}"
    payload: dict[str, Any] = {
        "intent_id": intent_id,
        "methodology": methodology,
        "mapping_id": mapping_id,
        "forge_projection_label": forge_label,
        "delivery_mode": mode,
        "recurrence": recurrence,
        "inputs": inputs,
        "status": "planned",
        "created_at": _now_iso(),
    }
    title = str(body.get("title") or tpl.get("display_name") or f"Ceremony {intent_id}").strip()[:200]
    upsert_ogs_entity(
        conn,
        entity_id=iid,
        kind="ceremony_instance",
        display_name=title,
        summary=str(body.get("summary") or forge_label)[:500],
        payload=payload,
        source_system="ceremony_b4",
        source_record_id=mapping_id,
    )
    r1 = insert_bridge_link(
        conn,
        from_id=iid,
        to_id=template_id,
        kind="instantiates",
        source_system="ceremony_b4",
        source_record_id="instance_template",
    )
    if not r1.get("ok"):
        return r1
    r2 = insert_bridge_link(
        conn,
        from_id=iid,
        to_id=dm_entity,
        kind="references",
        source_system="ceremony_b4",
        source_record_id="instance_delivery_mode",
    )
    if not r2.get("ok"):
        return r2

    for wid in inputs.get("work_unit_ids") or []:
        w = str(wid).strip()
        if w and fetch_entity(conn, w):
            insert_bridge_link(
                conn,
                from_id=iid,
                to_id=w,
                kind="references",
                source_system="ceremony_b4",
                source_record_id="input_work_unit",
            )
    conn.commit()
    return {"ok": True, "id": iid, "payload": payload}


def add_ceremony_output(conn: sqlite3.Connection, instance_id: str, body: dict[str, Any]) -> dict[str, Any]:
    reg = load_ceremony_bridge_registry()
    inst = fetch_entity(conn, instance_id)
    if inst is None or str(inst.get("kind")) != "ceremony_instance":
        return {"ok": False, "error": "ceremony_instance_not_found"}

    ip = _row_payload(inst)
    mode = str(ip.get("delivery_mode") or "")
    dm_rule = delivery_mode_rules(reg, mode)
    if dm_rule is None:
        return {"ok": False, "error": "instance_delivery_mode_invalid"}

    output_type = str(body.get("output_type") or "").strip()
    if not output_type:
        return {"ok": False, "error": "output_type_required"}

    binding = is_binding_output_type(reg, output_type)
    if binding and not bool(dm_rule.get("allow_binding_outputs", False)):
        return {
            "ok": False,
            "error": "binding_output_not_allowed_for_delivery_mode",
            "delivery_mode": mode,
        }
    if binding and bool(dm_rule.get("binding_requires_human_signoff", True)):
        if not _instance_has_human_signoff(conn, instance_id):
            return {
                "ok": False,
                "error": "binding_requires_human_signoff",
                "detail": "Record sign-off on the instance before adding binding outputs.",
            }

    oid = str(body.get("id") or "").strip() or f"ogs:b4:out:{uuid.uuid4().hex[:12]}"
    out_payload: dict[str, Any] = {
        "output_type": output_type,
        "binding": binding,
        "delivery_mode": mode,
        "summary": str(body.get("summary") or "")[:4000],
        "created_at": _now_iso(),
    }
    title = str(body.get("title") or f"Output — {output_type}").strip()[:200]
    upsert_ogs_entity(
        conn,
        entity_id=oid,
        kind="ceremony_output",
        display_name=title,
        summary=out_payload["summary"][:500],
        payload=out_payload,
        source_system="ceremony_b4",
        source_record_id=output_type,
    )
    r = insert_bridge_link(
        conn,
        from_id=instance_id,
        to_id=oid,
        kind="yields_output",
        source_system="ceremony_b4",
        source_record_id="ceremony_output",
    )
    if not r.get("ok"):
        return r

    for lk in ("linked_decision_id", "linked_evidence_id", "linked_review_pack_id", "linked_assay_id", "linked_task_id"):
        lid = str(body.get(lk) or "").strip()
        if not lid:
            continue
        target = fetch_entity(conn, lid)
        if target is None:
            continue
        insert_bridge_link(
            conn,
            from_id=oid,
            to_id=lid,
            kind="references",
            source_system="ceremony_b4",
            source_record_id=lk,
        )
    conn.commit()
    return {"ok": True, "id": oid, "payload": out_payload}


def signoff_ceremony(conn: sqlite3.Connection, instance_id: str, body: dict[str, Any]) -> dict[str, Any]:
    inst = fetch_entity(conn, instance_id)
    if inst is None or str(inst.get("kind")) != "ceremony_instance":
        return {"ok": False, "error": "ceremony_instance_not_found"}
    signed_by = str(body.get("signed_by") or body.get("login") or "").strip()
    if not signed_by:
        return {"ok": False, "error": "signed_by_required"}
    if not bool(body.get("confirm_human_signoff")):
        return {"ok": False, "error": "confirm_human_signoff_required"}

    sid = str(body.get("signoff_id") or "").strip() or f"ogs:b4:so:{uuid.uuid4().hex[:12]}"
    role = str(body.get("signer_role") or "governance_delegate").strip()
    sp = {
        "state": "signed",
        "signed_by": signed_by,
        "signer_role": role,
        "signed_at": _now_iso(),
        "scope": str(body.get("scope") or "ceremony_instance")[:500],
    }
    upsert_ogs_entity(
        conn,
        entity_id=sid,
        kind="signoff_record",
        display_name=f"Sign-off — {signed_by}"[:200],
        summary=f"Human sign-off for {instance_id}"[:500],
        payload=sp,
        source_system="ceremony_b4",
        source_record_id=instance_id,
    )
    r = insert_bridge_link(
        conn,
        from_id=sid,
        to_id=instance_id,
        kind="approves",
        source_system="ceremony_b4",
        source_record_id="ceremony_signoff",
    )
    if not r.get("ok"):
        return r
    ip = _row_payload(inst)
    ip["last_signoff_at"] = sp["signed_at"]
    ip["last_signoff_by"] = signed_by
    now = _now_iso()
    conn.execute(
        "UPDATE ogs_entity SET payload_json = ?, updated_at = ? WHERE id = ?",
        (json.dumps(ip, separators=(",", ":"), sort_keys=True), now, instance_id),
    )
    conn.commit()
    return {"ok": True, "id": sid, "instance_id": instance_id, "payload": sp}


def ceremony_instance_bundle(conn: sqlite3.Connection, instance_id: str) -> dict[str, Any]:
    inst = fetch_entity(conn, instance_id)
    if inst is None or str(inst.get("kind")) != "ceremony_instance":
        return {"ok": False, "error": "ceremony_instance_not_found"}
    tpl = _template_for_instance(conn, instance_id)
    intent_ent = None
    map_ent = None
    if tpl:
        intent_ent = _intent_entity_for_template(conn, str(tpl.get("id") or ""))
        map_ent = _mapping_entity_for_template(conn, str(tpl.get("id") or ""))
    outs = _outputs_for_instance(conn, instance_id)
    sigs = _signoffs_for_instance(conn, instance_id)
    fus = _followups_for_instance(conn, instance_id)
    return {
        "ok": True,
        "instance": inst,
        "template": tpl,
        "ceremony_intent": intent_ent,
        "ceremony_mapping_entity": map_ent,
        "outputs": outs,
        "signoffs": sigs,
        "followups": fus,
    }


def agenda_payload(conn: sqlite3.Connection, instance_id: str) -> dict[str, Any]:
    b = ceremony_instance_bundle(conn, instance_id)
    if not b.get("ok"):
        return b
    reg = load_ceremony_bridge_registry()
    inst = b["instance"]
    ip = _row_payload(inst)
    tpl = b.get("template") or {}
    tp = _row_payload(tpl) if tpl else {}
    rt = _resolve_registry_template(conn, tpl) if tpl else None
    mid = str(ip.get("mapping_id") or "")
    rm = registry_mapping_by_id(reg, mid)
    intents = merged_ceremony_intents_payload()
    cid = str(ip.get("intent_id") or "")
    neutral = (intents.get("intents") or {}).get(cid) if isinstance(intents.get("intents"), dict) else None
    prereads = []
    if isinstance(rt, dict):
        prereads = list(rt.get("required_prereads") or [])
    agenda_items = [
        {"step": 1, "title": "Framing", "detail": neutral.get("neutral_label") if isinstance(neutral, dict) else cid},
        {"step": 2, "title": "Mapped Forge ritual", "detail": rm.get("forge_ritual") if rm else ip.get("forge_projection_label")},
        {"step": 3, "title": "Pre-reads", "detail": prereads},
        {
            "step": 4,
            "title": "Delivery mode",
            "detail": {"mode": ip.get("delivery_mode"), "rules": delivery_mode_rules(reg, str(ip.get("delivery_mode") or ""))},
        },
    ]
    return {
        "ok": True,
        "instance_id": instance_id,
        "title": inst.get("display_name"),
        "agenda": agenda_items,
        "registry_version": reg.get("registry_version"),
        "template_registry_id": tp.get("registry_template_id"),
    }


def readiness_payload(conn: sqlite3.Connection, instance_id: str) -> dict[str, Any]:
    b = ceremony_instance_bundle(conn, instance_id)
    if not b.get("ok"):
        return b
    reg = load_ceremony_bridge_registry()
    inst = b["instance"]
    ip = _row_payload(inst)
    tpl = b.get("template") or {}
    rt = _resolve_registry_template(conn, tpl) if tpl else None
    required_outputs: list[str] = []
    required_signoff_roles: list[str] = []
    if isinstance(rt, dict):
        required_outputs = [str(x) for x in (rt.get("required_outputs") or []) if isinstance(x, str)]
        required_signoff_roles = [str(x) for x in (rt.get("required_signoff_roles") or []) if isinstance(x, str)]

    have_types: set[str] = set()
    for o in b.get("outputs") or []:
        op = _row_payload(o if isinstance(o, dict) else {})
        ot = str(op.get("output_type") or "").strip()
        if ot:
            have_types.add(ot)

    missing_outputs = [x for x in required_outputs if x not in have_types]
    has_signoff = _instance_has_human_signoff(conn, instance_id)
    missing_signoffs: list[str] = []
    if required_signoff_roles and not has_signoff:
        missing_signoffs = list(required_signoff_roles)

    inp = ip.get("inputs") if isinstance(ip.get("inputs"), dict) else {}
    missing_inputs: list[str] = []
    if not (inp.get("work_unit_ids") or []):
        missing_inputs.append("work_unit_ids")
    if not (inp.get("artifact_ids") or []):
        missing_inputs.append("artifact_ids")
    if not (inp.get("evidence_ids") or []):
        missing_inputs.append("evidence_ids")
    if inp.get("metrics_snapshot") is None:
        missing_inputs.append("metrics_snapshot")
    if not (inp.get("risks_issues") or []):
        missing_inputs.append("risks_issues")

    complete = not missing_outputs and not missing_signoffs and not missing_inputs
    return {
        "ok": True,
        "instance_id": instance_id,
        "complete": complete,
        "missing_required_outputs": missing_outputs,
        "missing_signoffs": missing_signoffs,
        "missing_inputs": missing_inputs,
        "required_outputs": required_outputs,
        "delivery_mode": ip.get("delivery_mode"),
    }


def mapping_inspector_row(conn: sqlite3.Connection, instance_id: str) -> dict[str, Any]:
    b = ceremony_instance_bundle(conn, instance_id)
    if not b.get("ok"):
        return {"ok": False, "error": b.get("error")}
    inst = b["instance"]
    ip = _row_payload(inst)
    tpl = b.get("template") or {}
    tp = _row_payload(tpl)
    reg = load_ceremony_bridge_registry()
    mid = str(ip.get("mapping_id") or "")
    rm = registry_mapping_by_id(reg, mid)
    rd = readiness_payload(conn, instance_id)
    return {
        "ok": True,
        "neutral_intent": ip.get("intent_id"),
        "neutral_label": (merged_ceremony_intents_payload().get("intents") or {}).get(str(ip.get("intent_id") or ""), {}),
        "methodology": ip.get("methodology"),
        "mapped_forge_ritual": rm.get("forge_ritual") if rm else None,
        "forge_projection_label": ip.get("forge_projection_label"),
        "delivery_mode": ip.get("delivery_mode"),
        "template_registry_id": tp.get("registry_template_id"),
        "required_outputs": rd.get("required_outputs"),
        "completeness": {
            "complete": rd.get("complete"),
            "required_outputs": rd.get("required_outputs"),
            "missing_required_outputs": rd.get("missing_required_outputs"),
            "missing_signoffs": rd.get("missing_signoffs"),
            "missing_inputs": rd.get("missing_inputs"),
        },
    }
