"""Portfolio alignment, scenarios, dependencies, critical path — Sprint 2 (canonical graph)."""

from __future__ import annotations

import json
import sqlite3
from collections import defaultdict, deque
from typing import Any

from lenses.orchestration_graph.query import fetch_entity


def _payload(row: sqlite3.Row) -> dict[str, Any]:
    try:
        p = json.loads(row["payload_json"] or "{}")
        return p if isinstance(p, dict) else {}
    except json.JSONDecodeError:
        return {}


def _all_entities(conn: sqlite3.Connection) -> dict[str, sqlite3.Row]:
    return {str(r["id"]): r for r in conn.execute("SELECT * FROM ogs_entity")}


def _edges_by_kind(conn: sqlite3.Connection, kind: str) -> list[sqlite3.Row]:
    return list(conn.execute("SELECT * FROM ogs_edge WHERE kind = ?", (kind,)))


def story_entity_index(conn: sqlite3.Connection) -> dict[str, str]:
    """Map WBS-style story id (payload ``story_id``) → ogs entity id."""
    out: dict[str, str] = {}
    for r in conn.execute("SELECT id, payload_json FROM ogs_entity WHERE kind = 'story'"):
        p = _payload(r)
        sid = str(p.get("story_id") or "").strip()
        if sid:
            out[sid] = str(r["id"])
    return out


def depends_on_in_degree(conn: sqlite3.Connection) -> dict[str, int]:
    """Count incoming ``depends_on`` (how many others must finish before this one)."""
    indeg: dict[str, int] = defaultdict(int)
    for r in _edges_by_kind(conn, "depends_on"):
        blocked = str(r["from_id"])
        indeg[blocked] += 1
    return dict(indeg)


def depends_on_graph(conn: sqlite3.Connection) -> tuple[dict[str, list[str]], dict[str, list[str]]]:
    """``depends_on`` edge: from_id blocked until to_id done → adjacency to_id → [from_id…]."""
    forward: dict[str, list[str]] = defaultdict(list)
    reverse: dict[str, list[str]] = defaultdict(list)
    for r in _edges_by_kind(conn, "depends_on"):
        blocked = str(r["from_id"])
        prereq = str(r["to_id"])
        forward[prereq].append(blocked)
        reverse[blocked].append(prereq)
    return dict(forward), dict(reverse)


def downstream_blocked_by(conn: sqlite3.Connection, entity_id: str) -> list[str]:
    """Entities that transitively **block** if ``entity_id`` slips (BFS on reverse depends_on)."""
    _, rev = depends_on_graph(conn)
    seen: set[str] = set()
    q: deque[str] = deque([entity_id])
    while q:
        cur = q.popleft()
        for nxt in rev.get(cur, []):
            if nxt not in seen:
                seen.add(nxt)
                q.append(nxt)
    return sorted(seen - {entity_id})


def critical_path_depends_on(
    conn: sqlite3.Connection,
    *,
    kinds: frozenset[str] = frozenset({"story", "epic", "task", "initiative"}),
) -> dict[str, Any]:
    """
    Longest path in DAG implied by ``depends_on`` (unit duration per node unless payload has duration_days).

    Edge semantics: ``from`` depends on ``to`` → ``to`` must finish before ``from`` → topo edge **to → from**.
    """
    entities = _all_entities(conn)
    nodes: set[str] = {
        eid for eid, row in entities.items() if str(row["kind"]) in kinds
    }
    if not nodes:
        return {"ok": True, "path": [], "length": 0.0, "tip_entity_id": None}

    adj: dict[str, list[str]] = defaultdict(list)
    indeg0: dict[str, int] = defaultdict(int)
    for r in _edges_by_kind(conn, "depends_on"):
        blocked = str(r["from_id"])
        prereq = str(r["to_id"])
        if blocked not in nodes or prereq not in nodes:
            continue
        adj[prereq].append(blocked)
        indeg0[blocked] += 1
        indeg0.setdefault(prereq, 0)

    for n in nodes:
        indeg0.setdefault(n, 0)

    indeg_t = dict(indeg0)
    q = deque([n for n in nodes if indeg_t.get(n, 0) == 0])
    topo: list[str] = []
    while q:
        u = q.popleft()
        topo.append(u)
        for v in adj.get(u, []):
            indeg_t[v] -= 1
            if indeg_t[v] == 0:
                q.append(v)

    if len(topo) != len(nodes):
        return {
            "ok": False,
            "error": "cycle_in_depends_on",
            "path": [],
            "length": 0,
        }

    weight: dict[str, float] = {}
    for n in nodes:
        p = _payload(entities[n])
        try:
            d = float(p.get("duration_days", 1))
        except (TypeError, ValueError):
            d = 1.0
        weight[n] = max(0.1, d)

    dist: dict[str, float] = {n: 0.0 for n in nodes}
    pred: dict[str, str | None] = {n: None for n in nodes}
    for u in topo:
        for v in adj.get(u, []):
            alt = dist[u] + weight[v]
            if alt > dist[v]:
                dist[v] = alt
                pred[v] = u

    end = max(nodes, key=lambda n: dist.get(n, 0.0))
    path: list[str] = []
    cur: str | None = end
    while cur is not None:
        path.append(cur)
        cur = pred.get(cur)
    path.reverse()

    return {
        "ok": True,
        "path": path,
        "length": round(dist.get(end, 0.0), 2),
        "tip_entity_id": end,
    }


def graph_completeness_score(conn: sqlite3.Connection) -> dict[str, Any]:
    """0–100 score from story linkage (PR, evidence, not orphaned in depends_on)."""
    stories = list(conn.execute("SELECT id FROM ogs_entity WHERE kind = 'story'"))
    if not stories:
        return {"score": 0, "story_count": 0, "details": {"no_stories": True}}

    has_impl = {str(r["to_id"]) for r in _edges_by_kind(conn, "implements")}
    has_doc = {str(r["from_id"]) for r in _edges_by_kind(conn, "documented_by")}
    indeg = depends_on_in_degree(conn)

    scores: list[float] = []
    for r in stories:
        sid = str(r["id"])
        pts = 0.0
        if sid in has_impl:
            pts += 40
        if sid in has_doc:
            pts += 35
        if indeg.get(sid, 0) > 0:
            pts += 15
        pts += 10
        scores.append(min(100.0, pts))

    avg = sum(scores) / len(scores) if scores else 0.0
    return {
        "score": round(avg, 1),
        "story_count": len(stories),
        "details": {
            "stories_with_pr_edge": len(has_impl & {str(r["id"]) for r in stories}),
            "stories_with_evidence": len(has_doc & {str(r["id"]) for r in stories}),
        },
    }


def portfolio_rollups(conn: sqlite3.Connection) -> dict[str, Any]:
    indeg = depends_on_in_degree(conn)
    max_pressure = max(indeg.values(), default=0)
    vuln_n = int(
        conn.execute("SELECT COUNT(*) AS c FROM ogs_entity WHERE kind = 'vulnerability'").fetchone()["c"]
    )
    open_inc = int(
        conn.execute("SELECT COUNT(*) AS c FROM ogs_entity WHERE kind = 'incident'").fetchone()["c"]
    )
    comp = graph_completeness_score(conn)
    scenarios = list_scenario_entities(conn)
    baseline_conf = None
    for s in scenarios:
        p = s.get("payload") or {}
        if p.get("is_baseline"):
            try:
                baseline_conf = float(p.get("milestone_confidence", 0))
            except (TypeError, ValueError):
                baseline_conf = None
            break
    if baseline_conf is None and scenarios:
        try:
            baseline_conf = float((scenarios[0].get("payload") or {}).get("milestone_confidence", 0))
        except (TypeError, ValueError):
            baseline_conf = None

    cp = critical_path_depends_on(conn)

    return {
        "dependency_pressure_max": max_pressure,
        "open_vulnerabilities": vuln_n,
        "incidents_open_heuristic": open_inc,
        "graph_completeness": comp,
        "milestone_confidence_baseline": baseline_conf,
        "critical_path": cp,
    }


def list_scenario_entities(conn: sqlite3.Connection) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for r in conn.execute("SELECT * FROM ogs_entity WHERE kind = 'scenario' ORDER BY id"):
        out.append(
            {
                "id": str(r["id"]),
                "display_name": str(r["display_name"]),
                "summary": str(r["summary"] or ""),
                "payload": _payload(r),
            }
        )
    return out


def compare_scenarios(
    conn: sqlite3.Connection,
    scenario_a: str,
    scenario_b: str,
) -> dict[str, Any]:
    ra = conn.execute("SELECT * FROM ogs_entity WHERE id = ?", (scenario_a,)).fetchone()
    rb = conn.execute("SELECT * FROM ogs_entity WHERE id = ?", (scenario_b,)).fetchone()
    if not ra or str(ra["kind"]) != "scenario":
        return {"ok": False, "error": "scenario_a_not_found"}
    if not rb or str(rb["kind"]) != "scenario":
        return {"ok": False, "error": "scenario_b_not_found"}
    pa, pb = _payload(ra), _payload(rb)

    def num(keys: list[str]) -> dict[str, float | None]:
        d: dict[str, float | None] = {}
        for k in keys:
            try:
                va = float(pa.get(k)) if pa.get(k) is not None else None
                vb = float(pb.get(k)) if pb.get(k) is not None else None
                if va is not None and vb is not None:
                    d[k] = round(vb - va, 4)
                else:
                    d[k] = None
            except (TypeError, ValueError):
                d[k] = None
        return d

    keys = ["horizon_shift_days", "capacity_scale", "risk_score", "milestone_confidence"]
    return {
        "ok": True,
        "a": {
            "id": scenario_a,
            "display_name": str(ra["display_name"]),
            "payload": pa,
        },
        "b": {
            "id": scenario_b,
            "display_name": str(rb["display_name"]),
            "payload": pb,
        },
        "delta_numeric": num(keys),
    }


def workstream_capacity_placeholder(conn: sqlite3.Connection) -> list[dict[str, Any]]:
    """Placeholder allocation: sum ``allocated_to`` edges into each workstream."""
    rows = list(conn.execute("SELECT * FROM ogs_entity WHERE kind = 'workstream'"))
    incoming: dict[str, int] = defaultdict(int)
    for r in _edges_by_kind(conn, "allocated_to"):
        ws = str(r["to_id"])
        incoming[ws] += 1

    out: list[dict[str, Any]] = []
    for r in rows:
        eid = str(r["id"])
        p = _payload(r)
        try:
            cap = float(p.get("capacity_units", 0))
        except (TypeError, ValueError):
            cap = 0.0
        alloc = float(incoming.get(eid, 0))
        out.append(
            {
                "id": eid,
                "display_name": str(r["display_name"]),
                "capacity_units": cap,
                "allocated_stories": incoming.get(eid, 0),
                "utilization": round(alloc / cap, 3) if cap > 0 else None,
                "payload": p,
            }
        )
    return sorted(out, key=lambda x: x["id"])


def dependency_edges_public(conn: sqlite3.Connection) -> list[dict[str, str]]:
    ent = _all_entities(conn)
    edges: list[dict[str, str]] = []
    for r in _edges_by_kind(conn, "depends_on"):
        fr = ent.get(str(r["from_id"]))
        to = ent.get(str(r["to_id"]))
        edges.append(
            {
                "from_id": str(r["from_id"]),
                "to_id": str(r["to_id"]),
                "from_kind": str(fr["kind"]) if fr else "",
                "to_kind": str(to["kind"]) if to else "",
            }
        )
    return edges


def enrich_milestone_row_with_graph(
    conn: sqlite3.Connection,
    milestone_row: dict[str, Any],
    story_index: dict[str, str],
) -> None:
    """Attach ``orchestration`` summary to one matrix milestone row (mutates)."""
    indeg = depends_on_in_degree(conn)
    pressure = 0
    linked = 0
    story_entity_ids: list[str] = []
    by_wbs = milestone_row.get("by_wbs") or {}
    if isinstance(by_wbs, dict):
        for _wbs, cell in by_wbs.items():
            if not isinstance(cell, dict):
                continue
            for st in cell.get("stories") or []:
                if not isinstance(st, dict):
                    continue
                sid = str(st.get("id") or "").strip()
                eid = story_index.get(sid)
                if eid:
                    linked += 1
                    story_entity_ids.append(eid)
                    pressure = max(pressure, indeg.get(eid, 0))
    slip_demo = None
    if story_entity_ids:
        slip_demo = {
            "for_entity_id": story_entity_ids[0],
            "transitive_blocked_count": len(downstream_blocked_by(conn, story_entity_ids[0])),
        }
    milestone_row["orchestration"] = {
        "linked_story_count": linked,
        "max_dependency_pressure": pressure,
        "slip_preview": slip_demo,
    }


def build_matrix_portfolio_overlay(
    conn: sqlite3.Connection,
    matrix_payload: dict[str, Any],
) -> dict[str, Any]:
    """Top-level bundle embedded in roadmaps-matrix response."""
    story_index = story_entity_index(conn)
    rollups = portfolio_rollups(conn)
    scenarios = list_scenario_entities(conn)
    deps = dependency_edges_public(conn)
    capacity = workstream_capacity_placeholder(conn)
    return {
        "schema_version": 1,
        "rollups": rollups,
        "scenarios": scenarios,
        "depends_on_edges": deps,
        "workstreams": capacity,
        "story_id_index_size": len(story_index),
    }


def apply_milestone_graph_enrichment(conn: sqlite3.Connection, matrix_payload: dict[str, Any]) -> None:
    if not matrix_payload.get("ok"):
        return
    story_index = story_entity_index(conn)
    for rm in matrix_payload.get("roadmaps") or []:
        if not isinstance(rm, dict):
            continue
        for ms in rm.get("milestones") or []:
            if isinstance(ms, dict):
                enrich_milestone_row_with_graph(conn, ms, story_index)


def build_timeline_portfolio_overlay(conn: sqlite3.Connection) -> dict[str, Any]:
    """Smaller bundle for timeline view (rollups + scenarios + slip hint)."""
    rollups = portfolio_rollups(conn)
    demo_story = "ogs:demo:story:rate-limit-auth"
    slip = None
    if fetch_entity(conn, demo_story):
        slip = {
            "if_entity_slips": demo_story,
            "transitive_blocked": downstream_blocked_by(conn, demo_story),
        }
    return {
        "schema_version": 1,
        "rollups": rollups,
        "scenarios": list_scenario_entities(conn),
        "slip_impact_demo": slip,
    }


def portfolio_context_payload(
    conn: sqlite3.Connection,
    *,
    scenario_a: str | None,
    scenario_b: str | None,
    slip_focus_id: str | None,
) -> dict[str, Any]:
    """Full Sprint-2 planning cockpit payload (Plan tab)."""
    rollups = portfolio_rollups(conn)
    scenarios = list_scenario_entities(conn)
    compare: dict[str, Any] | None = None
    if scenario_a and scenario_b and scenario_a.strip() and scenario_b.strip():
        compare = compare_scenarios(conn, scenario_a.strip(), scenario_b.strip())
    slip: dict[str, Any] | None = None
    fid = (slip_focus_id or "").strip()
    if fid and fetch_entity(conn, fid):
        slip = {
            "focus_entity_id": fid,
            "transitive_blocked": downstream_blocked_by(conn, fid),
        }
    return {
        "ok": True,
        "schema_version": 1,
        "rollups": rollups,
        "scenarios": scenarios,
        "scenario_compare": compare,
        "slip_impact": slip,
        "depends_on_edges": dependency_edges_public(conn),
        "workstreams": workstream_capacity_placeholder(conn),
        "graph_completeness": graph_completeness_score(conn),
    }


def plan_spine_orchestration_summary(conn: sqlite3.Connection) -> dict[str, Any]:
    """Compact object merged under plan-spine ``orchestration`` key."""
    comp = graph_completeness_score(conn)
    roll = portfolio_rollups(conn)
    return {
        "graph_completeness_score": comp.get("score"),
        "graph_completeness_detail": comp,
        "dependency_pressure_max": roll.get("dependency_pressure_max"),
        "critical_path": roll.get("critical_path"),
        "scenarios": [{"id": s["id"], "display_name": s["display_name"]} for s in list_scenario_entities(conn)],
    }
