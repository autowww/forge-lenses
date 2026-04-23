"""Sprint B6 — PDLC outcome bridge: launches, signals, learning summaries, follow-on Ore."""

from __future__ import annotations

import hashlib
import json
import uuid
from datetime import datetime, timezone
from typing import Any

import sqlite3

from lenses.bridge.handoff_service import list_story_entity_ids_for_work_item
from lenses.bridge.methodology_service import upsert_ogs_entity
from lenses.bridge.pdlc_outcome_bridge_registry import load_pdlc_outcome_bridge_registry
from lenses.bridge.trace_service import insert_bridge_link
from lenses.orchestration_graph.query import fetch_entity, trace_subgraph


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _row_payload(ent: dict[str, Any] | None) -> dict[str, Any]:
    if not ent or not isinstance(ent.get("payload"), dict):
        return {}
    return dict(ent["payload"])


B6_TYPED_SIGNAL_KINDS: frozenset[str] = frozenset(
    {
        "adoption_signal",
        "retention_signal",
        "support_signal",
        "satisfaction_signal",
        "revenue_proxy_signal",
    }
)

B6_OUTCOME_KINDS: frozenset[str] = frozenset(
    {
        "launch_record",
        "outcome_signal",
        "metric_snapshot",
        "experiment_result",
        "customer_feedback_ref",
        "learning_summary",
        "followon_ore_candidate",
    }
) | B6_TYPED_SIGNAL_KINDS


def releases_touching_story(conn: sqlite3.Connection, story_id: str) -> list[str]:
    t = trace_subgraph(conn, story_id, max_depth=14, max_nodes=450)
    if not t.get("ok"):
        return []
    return sorted({str(n["id"]) for n in t["nodes"] if n.get("kind") == "release"})


def launch_records_for_releases(conn: sqlite3.Connection, release_ids: list[str]) -> list[str]:
    if not release_ids:
        return []
    out: list[str] = []
    for rid in release_ids:
        for row in conn.execute(
            """
            SELECT e.from_id FROM ogs_edge e
            JOIN ogs_entity ent ON ent.id = e.from_id
            WHERE e.to_id = ? AND e.kind = 'launch_for' AND ent.kind = 'launch_record'
            """,
            (rid,),
        ):
            out.append(str(row["from_id"]))
    return list(dict.fromkeys(out))


def list_launches_for_work_item(conn: sqlite3.Connection, work_item_id: str) -> list[str]:
    sids = list_story_entity_ids_for_work_item(conn, work_item_id)
    if not sids:
        sids = [work_item_id.strip()]
    launches: list[str] = []
    for sid in sids:
        rels = releases_touching_story(conn, sid)
        launches.extend(launch_records_for_releases(conn, rels))
    return list(dict.fromkeys(launches))


def _signals_for_launch(conn: sqlite3.Connection, launch_id: str) -> list[dict[str, Any]]:
    rows = conn.execute(
        """
        SELECT ent.* FROM ogs_edge ex
        JOIN ogs_entity ent ON ent.id = ex.from_id
        WHERE ex.to_id = ? AND ex.kind = 'outcome_observed'
        ORDER BY ent.updated_at DESC
        """,
        (launch_id,),
    ).fetchall()
    return [dict(r) for r in rows]


def _release_for_launch(conn: sqlite3.Connection, launch_id: str) -> str | None:
    row = conn.execute(
        "SELECT to_id FROM ogs_edge WHERE from_id = ? AND kind = 'launch_for' LIMIT 1",
        (launch_id,),
    ).fetchone()
    return str(row["to_id"]) if row else None


def explain_scores_for_launch(conn: sqlite3.Connection, launch_id: str) -> dict[str, Any]:
    reg = load_pdlc_outcome_bridge_registry()
    expected = list(reg.get("signal_categories_expected_for_launch") or [])
    signals = _signals_for_launch(conn, launch_id)
    kinds_present = {str(s.get("kind")) for s in signals}
    matched = [k for k in expected if k in kinds_present]
    completeness = (len(matched) / len(expected)) if expected else 1.0

    confidences: list[float] = []
    pending_interp = 0
    stale = 0
    now = datetime.now(timezone.utc)
    for s in signals:
        p = _row_payload(s)
        c = p.get("confidence")
        if isinstance(c, (int, float)):
            confidences.append(float(c))
        if str(p.get("interpretation_status") or "").lower() in ("", "pending", "triage"):
            pending_interp += 1
        fa = str(p.get("freshness_at") or p.get("observed_at") or "")
        if fa:
            try:
                ts = datetime.fromisoformat(fa.replace("Z", "+00:00"))
                if (now - ts).total_seconds() > 14 * 86400:
                    stale += 1
            except ValueError:
                stale += 1

    avg_conf = sum(confidences) / len(confidences) if confidences else 0.45
    launch_confidence = round(min(1.0, completeness * 0.5 + avg_conf * 0.5), 3)
    ambiguity = round(min(1.0, pending_interp / max(1, len(signals))), 3)

    # learning_summary --aggregates--> signal --outcome_observed--> launch
    learning_ids: set[str] = set()
    for s in signals:
        sid = str(s.get("id") or "")
        for r in conn.execute(
            "SELECT from_id FROM ogs_edge WHERE to_id = ? AND kind = 'aggregates'",
            (sid,),
        ):
            le = fetch_entity(conn, str(r["from_id"]))
            if le and str(le.get("kind")) == "learning_summary":
                learning_ids.add(str(le["id"]))

    followon_count = 0
    demand_linked = 0
    for lid in learning_ids:
        for r in conn.execute(
            "SELECT to_id FROM ogs_edge WHERE from_id = ? AND kind = 'proposes_followon'",
            (lid,),
        ):
            fid = str(r["to_id"])
            fo = fetch_entity(conn, fid)
            if fo and str(fo.get("kind")) == "followon_ore_candidate":
                followon_count += 1
                r2 = conn.execute(
                    "SELECT to_id FROM ogs_edge WHERE from_id = ? AND kind = 'bridges_to_demand'",
                    (fid,),
                ).fetchone()
                if r2:
                    demand_linked += 1

    explanations: list[str] = [
        f"Evidence completeness: {len(matched)}/{len(expected)} expected signal categories present "
        f"({', '.join(matched) or 'none'}).",
        f"Average signal confidence: {avg_conf:.2f} (from {len(confidences)} signals with numeric confidence).",
        f"Signals with pending interpretation: {pending_interp} (ambiguity proxy {ambiguity}).",
        f"Signals older than 14d or missing freshness: {stale}.",
        f"Learning summaries tied to this launch: {len(learning_ids)}; "
        f"follow-on Ore candidates: {followon_count}; linked demand rows: {demand_linked}.",
    ]

    return {
        "ok": True,
        "launch_id": launch_id,
        "launch_confidence": launch_confidence,
        "evidence_completeness": round(completeness, 3),
        "signal_freshness_notes": {
            "stale_or_unknown_freshness_count": stale,
            "signal_count": len(signals),
        },
        "outcome_ambiguity": ambiguity,
        "followon_demand": {
            "followon_candidates": followon_count,
            "demand_signals_linked": demand_linked,
            "ignored_followon_hint": followon_count > demand_linked,
        },
        "explanations": explanations,
    }


def get_launch_bundle(conn: sqlite3.Connection, launch_id: str) -> dict[str, Any]:
    ent = fetch_entity(conn, launch_id)
    if ent is None or str(ent.get("kind")) != "launch_record":
        return {"ok": False, "error": "launch_record_not_found"}
    rid = _release_for_launch(conn, launch_id)
    release = fetch_entity(conn, rid) if rid else None
    signals = _signals_for_launch(conn, launch_id)
    scores = explain_scores_for_launch(conn, launch_id)

    learnings: list[str] = []
    followons: list[str] = []
    demands: list[str] = []
    for s in signals:
        sid = str(s.get("id") or "")
        for r in conn.execute(
            "SELECT from_id FROM ogs_edge WHERE to_id = ? AND kind = 'aggregates'",
            (sid,),
        ):
            leid = str(r["from_id"])
            le = fetch_entity(conn, leid)
            if le and str(le.get("kind")) == "learning_summary":
                learnings.append(leid)
            for r2 in conn.execute(
                "SELECT to_id FROM ogs_edge WHERE from_id = ? AND kind = 'proposes_followon'",
                (leid,),
            ):
                fid = str(r2["to_id"])
                followons.append(fid)
                r3 = conn.execute(
                    "SELECT to_id FROM ogs_edge WHERE from_id = ? AND kind = 'bridges_to_demand'",
                    (fid,),
                ).fetchone()
                if r3:
                    demands.append(str(r3["to_id"]))

    return {
        "ok": True,
        "launch": ent,
        "release_id": rid,
        "release": release,
        "signals": signals,
        "scores": scores,
        "learning_summary_ids": list(dict.fromkeys(learnings)),
        "followon_ore_ids": list(dict.fromkeys(followons)),
        "demand_signal_ids": list(dict.fromkeys(demands)),
    }


def list_outcomes(conn: sqlite3.Connection, *, limit: int = 80) -> dict[str, Any]:
    lim = max(1, min(limit, 200))
    rows = conn.execute(
        """
        SELECT id, display_name, summary, payload_json, updated_at FROM ogs_entity
        WHERE kind = 'launch_record'
        ORDER BY updated_at DESC
        LIMIT ?
        """,
        (lim,),
    ).fetchall()
    items = []
    for r in rows:
        lid = str(r["id"])
        b = get_launch_bundle(conn, lid)
        items.append(
            {
                "id": lid,
                "display_name": r["display_name"],
                "summary": r["summary"],
                "updated_at": r["updated_at"],
                "release_id": b.get("release_id"),
                "signal_count": len(b.get("signals") or []),
                "scores": b.get("scores") if b.get("ok") else {},
            }
        )
    return {"ok": True, "launches": items}


def create_launch_record(conn: sqlite3.Connection, body: dict[str, Any]) -> dict[str, Any]:
    release_id = str(body.get("release_id") or "").strip()
    if not release_id:
        return {"ok": False, "error": "release_id_required"}
    rel = fetch_entity(conn, release_id)
    if rel is None or str(rel.get("kind")) != "release":
        return {"ok": False, "error": "release_not_found"}
    eid = str(body.get("id") or "").strip() or f"ogs:b6:launch:{uuid.uuid4().hex[:12]}"
    display_name = str(body.get("display_name") or "Launch record").strip()[:500]
    summary = str(body.get("summary") or "").strip()[:2000]
    base_payload = {
        "source": str(body.get("source") or "manual"),
        "time_window": body.get("time_window") if isinstance(body.get("time_window"), dict) else {},
        "scope": str(body.get("scope") or ""),
        "confidence": body.get("confidence", 0.7),
        "interpretation_status": str(body.get("interpretation_status") or "pending"),
        "owner": str(body.get("owner") or ""),
        "freshness_at": str(body.get("freshness_at") or _now_iso()),
    }
    extra = body.get("payload")
    if isinstance(extra, dict):
        base_payload.update(extra)
    upsert_ogs_entity(
        conn,
        entity_id=eid,
        kind="launch_record",
        display_name=display_name,
        summary=summary,
        payload=base_payload,
        source_system=str(body.get("source_system") or "outcome_b6"),
        source_record_id=str(body.get("source_record_id") or eid),
    )
    link = insert_bridge_link(
        conn,
        from_id=eid,
        to_id=release_id,
        kind="launch_for",
        source_system="outcome_b6",
        source_record_id="launch_for",
    )
    if not link.get("ok"):
        # duplicate launch_for triple — still ok if same release
        pass
    conn.commit()
    return {"ok": True, "launch_id": eid, "release_id": release_id, "edge": link}


def _normalize_outcome_kind(kind: str) -> str:
    k = kind.strip()
    if k in B6_OUTCOME_KINDS or k in B6_TYPED_SIGNAL_KINDS:
        return k
    return ""


def create_outcome_entity(conn: sqlite3.Connection, body: dict[str, Any]) -> dict[str, Any]:
    kind = _normalize_outcome_kind(str(body.get("kind") or ""))
    if not kind:
        return {"ok": False, "error": "invalid_or_missing_kind", "allowed_sample": sorted(B6_OUTCOME_KINDS)[:15]}
    eid = str(body.get("id") or "").strip() or f"ogs:b6:{kind}:{uuid.uuid4().hex[:10]}"
    display_name = str(body.get("display_name") or kind).strip()[:500]
    summary = str(body.get("summary") or "").strip()[:2000]
    payload: dict[str, Any] = {
        "source": str(body.get("source") or "manual"),
        "time_window": body.get("time_window") if isinstance(body.get("time_window"), dict) else {},
        "scope": str(body.get("scope") or ""),
        "confidence": float(body.get("confidence", 0.6)),
        "interpretation_status": str(body.get("interpretation_status") or "pending"),
        "owner": str(body.get("owner") or ""),
        "freshness_at": str(body.get("freshness_at") or _now_iso()),
    }
    ex = body.get("payload")
    if isinstance(ex, dict):
        payload.update(ex)
    upsert_ogs_entity(
        conn,
        entity_id=eid,
        kind=kind,
        display_name=display_name,
        summary=summary,
        payload=payload,
        source_system=str(body.get("source_system") or "outcome_b6"),
        source_record_id=str(body.get("source_record_id") or eid),
    )
    conn.commit()
    return {"ok": True, "entity_id": eid, "kind": kind}


def link_outcome_to_launch(conn: sqlite3.Connection, launch_id: str, body: dict[str, Any]) -> dict[str, Any]:
    launch = fetch_entity(conn, launch_id)
    if launch is None or str(launch.get("kind")) != "launch_record":
        return {"ok": False, "error": "launch_record_not_found"}
    oid = str(body.get("outcome_entity_id") or body.get("entity_id") or "").strip()
    if not oid:
        return {"ok": False, "error": "outcome_entity_id_required"}
    ot = fetch_entity(conn, oid)
    if ot is None:
        return {"ok": False, "error": "outcome_entity_not_found"}
    okind = str(ot.get("kind"))
    if okind not in B6_OUTCOME_KINDS and okind not in B6_TYPED_SIGNAL_KINDS:
        return {"ok": False, "error": "entity_not_an_outcome_signal", "kind": okind}
    lk = str(body.get("edge_kind") or "outcome_observed")
    if lk != "outcome_observed":
        return {"ok": False, "error": "only_outcome_observed_supported"}
    r = insert_bridge_link(
        conn,
        from_id=oid,
        to_id=launch_id,
        kind="outcome_observed",
        source_system="outcome_b6",
        source_record_id=str(body.get("source_record_id") or "outcome_observed"),
    )
    conn.commit()
    if not r.get("ok"):
        err = str(r.get("error") or "")
        if "edge_exists" in err or "constraint" in err.lower():
            return {"ok": True, "idempotent": True, "edge": r}
        return r
    return {"ok": True, "edge": r}


def trace_outcome_entity(conn: sqlite3.Connection, entity_id: str) -> dict[str, Any]:
    ent = fetch_entity(conn, entity_id)
    if ent is None:
        return {"ok": False, "error": "entity_not_found"}
    t = trace_subgraph(conn, entity_id, max_depth=12, max_nodes=400, direction="both")
    return {**t, "root_entity": ent}


def pdlc_bridge_for_entity(conn: sqlite3.Connection, entity_id: str) -> dict[str, Any]:
    ent = fetch_entity(conn, entity_id)
    if ent is None:
        return {"ok": False, "error": "entity_not_found"}
    reg = load_pdlc_outcome_bridge_registry()
    kind = str(ent.get("kind"))
    neutral = reg.get("neutral_to_pdlc") or {}
    if kind in B6_TYPED_SIGNAL_KINDS or kind == "outcome_signal":
        mapped = neutral.get("outcome_signal_family")
    else:
        mapped = neutral.get(kind)
    return {
        "ok": True,
        "entity_id": entity_id,
        "kind": kind,
        "registry_version": reg.get("registry_version"),
        "projection": mapped,
        "release_to_outcome_stage": reg.get("release_to_outcome_stage"),
        "followon_rules": reg.get("followon_generation_rules"),
    }


def create_followon_ore(
    conn: sqlite3.Connection,
    anchor_id: str,
    body: dict[str, Any],
) -> dict[str, Any]:
    anchor = fetch_entity(conn, anchor_id)
    if anchor is None:
        return {"ok": False, "error": "entity_not_found"}
    ak = str(anchor.get("kind"))
    if ak not in ("learning_summary", "launch_record"):
        return {"ok": False, "error": "anchor_must_be_learning_summary_or_launch_record"}

    idem = str(body.get("idempotency_key") or "").strip()
    if idem and ak == "learning_summary":
        hid = hashlib.sha256(f"{anchor_id}:{idem}".encode()).hexdigest()[:16]
        existing_demand = f"ogs:b6:demand:{hid}"
        ex = fetch_entity(conn, existing_demand)
        if ex:
            fod = ""
            r0 = conn.execute(
                "SELECT from_id FROM ogs_edge WHERE to_id = ? AND kind = 'bridges_to_demand'",
                (existing_demand,),
            ).fetchone()
            if r0:
                fod = str(r0["from_id"])
            return {
                "ok": True,
                "idempotent": True,
                "demand_signal_id": existing_demand,
                "followon_ore_candidate_id": fod,
                "learning_summary_id": anchor_id,
            }

    if ak == "learning_summary":
        learning_id = anchor_id
    else:
        # launch_record: pick first learning_summary linked via signals
        sigs = _signals_for_launch(conn, anchor_id)
        learning_id = ""
        for s in sigs:
            sid = str(s.get("id") or "")
            for r in conn.execute(
                "SELECT from_id FROM ogs_edge WHERE to_id = ? AND kind = 'aggregates'",
                (sid,),
            ):
                le = fetch_entity(conn, str(r["from_id"]))
                if le and str(le.get("kind")) == "learning_summary":
                    learning_id = str(le["id"])
                    break
            if learning_id:
                break
        if not learning_id:
            return {"ok": False, "error": "no_learning_summary_linked_to_launch"}

    if ak == "learning_summary":
        for r in conn.execute(
            "SELECT to_id FROM ogs_edge WHERE from_id = ? AND kind = 'proposes_followon'",
            (learning_id,),
        ):
            fid = str(r["to_id"])
            fo = fetch_entity(conn, fid)
            if fo and str(fo.get("kind")) == "followon_ore_candidate":
                r2 = conn.execute(
                    "SELECT to_id FROM ogs_edge WHERE from_id = ? AND kind = 'bridges_to_demand'",
                    (fid,),
                ).fetchone()
                if r2:
                    return {
                        "ok": True,
                        "idempotent": True,
                        "followon_ore_candidate_id": fid,
                        "demand_signal_id": str(r2["to_id"]),
                    }

    title = str(body.get("title") or "Follow-on Ore candidate").strip()[:500]
    demand_title = str(body.get("demand_title") or title).strip()[:500]
    summary = str(body.get("summary") or "").strip()[:2000]
    demand_summary = str(body.get("demand_summary") or summary).strip()[:2000]
    reason = str(body.get("reason") or "outcome_driven").strip()

    if idem:
        suffix = hashlib.sha256(f"{learning_id}:{idem}".encode()).hexdigest()[:14]
        fod_id = f"ogs:b6:followon:{suffix}"
        dem_id = f"ogs:b6:demand:{suffix}"
    else:
        suffix = uuid.uuid4().hex[:12]
        fod_id = f"ogs:b6:followon:{suffix}"
        dem_id = f"ogs:b6:demand:{suffix}"

    upsert_ogs_entity(
        conn,
        entity_id=fod_id,
        kind="followon_ore_candidate",
        display_name=title,
        summary=summary or "Generated from learning / outcome evidence",
        payload={
            "source": "outcome_b6",
            "reason": reason,
            "freshness_at": _now_iso(),
            "interpretation_status": "draft",
            "owner": str(body.get("owner") or ""),
        },
        source_system="outcome_b6",
        source_record_id="followon",
    )
    upsert_ogs_entity(
        conn,
        entity_id=dem_id,
        kind="demand_signal",
        display_name=demand_title,
        summary=demand_summary or "Demand derived from post-launch outcomes",
        payload={
            "source": "outcome_b6_followon",
            "reason": reason,
            "freshness_at": _now_iso(),
            "from_learning_id": learning_id,
        },
        source_system="outcome_b6",
        source_record_id=dem_id,
    )
    insert_bridge_link(
        conn,
        from_id=learning_id,
        to_id=fod_id,
        kind="proposes_followon",
        source_system="outcome_b6",
        source_record_id="proposes_followon",
    )
    insert_bridge_link(
        conn,
        from_id=fod_id,
        to_id=dem_id,
        kind="bridges_to_demand",
        source_system="outcome_b6",
        source_record_id="bridges_to_demand",
    )
    obj = str(body.get("objective_id") or "").strip()
    if obj:
        ob = fetch_entity(conn, obj)
        if ob and str(ob.get("kind")) == "objective":
            insert_bridge_link(
                conn,
                from_id=dem_id,
                to_id=obj,
                kind="originates_from",
                source_system="outcome_b6",
                source_record_id="originates_from",
            )
    conn.commit()
    return {
        "ok": True,
        "followon_ore_candidate_id": fod_id,
        "demand_signal_id": dem_id,
        "learning_summary_id": learning_id,
    }


def outcome_summary_for_work_item(conn: sqlite3.Connection, work_item_id: str) -> dict[str, Any] | None:
    lids = list_launches_for_work_item(conn, work_item_id)
    if not lids:
        return None
    rows = []
    for lid in lids[:4]:
        b = get_launch_bundle(conn, lid)
        if b.get("ok"):
            rows.append(
                {
                    "launch_id": lid,
                    "release_id": b.get("release_id"),
                    "signal_count": len(b.get("signals") or []),
                    "scores": b.get("scores"),
                    "learning_summary_ids": b.get("learning_summary_ids"),
                    "followon_ore_ids": b.get("followon_ore_ids"),
                    "demand_signal_ids": b.get("demand_signal_ids"),
                }
            )
    return {"outcome_launches": rows}
