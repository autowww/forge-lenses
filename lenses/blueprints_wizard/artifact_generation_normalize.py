"""Normalize ``wizard_domain.artifact_generation`` (Blueprint Wizard experimental, v2)."""

from __future__ import annotations

import copy
import secrets
from typing import Any

from lenses.blueprints_wizard.domain_enums import coerce_artifact_review_status

ARTIFACT_GENERATION_SCHEMA_VERSION = 2

ARTIFACT_SLICE_KEYS = (
    "foundation_brief_final",
    "assumptions_ledger",
    "roadmap",
    "milestone_outline",
    "milestone_charters",
    "wbe_tree",
    "dependency_map",
    "prd",
    "architecture_brief",
    "nfr_checklist",
    "adr_seeds",
    "ownership_review_matrix",
    "sparks_plan",
    "charge_plan",
    "implementation_tasklets",
    "acceptance_criteria",
    "execution_dependency_sequence",
    "qa_verification_checklist",
    "rollout_notes",
)

QUALITY_DIMENSIONS = (
    "groundedness",
    "completeness",
    "clarity",
    "consistency",
    "actionability",
    "traceability",
)

MAX_QUALITY_RATIONALE = 4_000
MAX_TRACE_REFS = 32
MAX_TRACE_REF_LEN = 500
MAX_LINEAGE_UPSTREAM = 32
MAX_POLICY_NOTES = 16
MAX_SPARK_ROWS = 256
MAX_CHARGE_ROWS = 128
MAX_TASKLET_ROWS = 256
MAX_UPSTREAM_REFS = 16
MAX_ACCEPTANCE_ROWS = 256
MAX_EXEC_SEQUENCE_STEPS = 256
MAX_QA_CHECKLIST_ITEMS = 256
MAX_ROLLOUT_SECTIONS = 32


def _coerce_str(v: Any) -> str:
    if v is None:
        return ""
    return str(v).strip()


def _new_id() -> str:
    return secrets.token_urlsafe(8)


def _clamp01(v: Any) -> float:
    try:
        x = float(v)
    except (TypeError, ValueError):
        return 0.0
    if x != x:  # NaN
        return 0.0
    return max(0.0, min(1.0, x))


def normalize_quality_dimension_entry(raw: Any) -> dict[str, Any]:
    defaults = {"score": 0.0, "rationale": ""}
    if not isinstance(raw, dict):
        return dict(defaults)
    out = {**defaults, **{k: v for k, v in raw.items() if k in ("score", "rationale")}}
    out["score"] = _clamp01(raw.get("score"))
    out["rationale"] = _coerce_str(raw.get("rationale"))[:MAX_QUALITY_RATIONALE]
    return out


def normalize_quality_rubric(raw: Any) -> dict[str, Any]:
    """Six dimensions, each { score: 0..1, rationale?: str }."""
    out: dict[str, Any] = {}
    if not isinstance(raw, dict):
        raw = {}
    for dim in QUALITY_DIMENSIONS:
        out[dim] = normalize_quality_dimension_entry(raw.get(dim))
    return out


def normalize_lineage_upstream(raw: Any) -> list[dict[str, Any]]:
    """List of upstream artifact snapshots at generation time (recheck / stale detection)."""
    if not isinstance(raw, list):
        return []
    out: list[dict[str, Any]] = []
    for item in raw[:MAX_LINEAGE_UPSTREAM]:
        if not isinstance(item, dict):
            continue
        ak = _coerce_str(item.get("artifact_key"))[:64]
        gid = _coerce_str(item.get("generation_id"))[:128]
        if not ak or not gid:
            continue
        rs = coerce_artifact_review_status(item.get("review_status"))
        out.append({"artifact_key": ak, "generation_id": gid, "review_status": rs})
    return out


def normalize_lineage(raw: Any) -> dict[str, Any]:
    defaults: dict[str, Any] = {"upstream": []}
    if not isinstance(raw, dict):
        return dict(defaults)
    out = {**defaults}
    out["upstream"] = normalize_lineage_upstream(raw.get("upstream"))
    return out


def normalize_provenance(raw: Any) -> dict[str, Any]:
    defaults = {
        "generation_id": "",
        "created_at": "",
        "provider": "",
        "model": "",
        "input_fingerprint": "",
        "parent_generation_id": "",
        "lineage": {"upstream": []},
    }
    if not isinstance(raw, dict):
        return {**defaults, "generation_id": _new_id(), "created_at": ""}
    scalar_keys = (
        "generation_id",
        "created_at",
        "provider",
        "model",
        "input_fingerprint",
        "parent_generation_id",
    )
    out = {**defaults}
    for k in scalar_keys:
        if k in raw:
            out[k] = _coerce_str(raw.get(k))
    out["generation_id"] = _coerce_str(raw.get("generation_id"))[:128] or _new_id()
    out["created_at"] = _coerce_str(raw.get("created_at"))[:64]
    out["provider"] = _coerce_str(raw.get("provider"))[:64]
    out["model"] = _coerce_str(raw.get("model"))[:200]
    out["input_fingerprint"] = _coerce_str(raw.get("input_fingerprint"))[:128]
    out["parent_generation_id"] = _coerce_str(raw.get("parent_generation_id"))[:128]
    lin = raw.get("lineage")
    out["lineage"] = normalize_lineage(lin if isinstance(lin, dict) else {})
    return out


def _normalize_fb_final_content(raw: Any) -> dict[str, Any]:
    from lenses.blueprints_wizard.wizard_domain_normalize import normalize_foundation_brief

    if not isinstance(raw, dict):
        raw = {}
    fb = normalize_foundation_brief({"markdown": raw.get("markdown", ""), "field_statuses": {}})
    return {"markdown": fb["markdown"]}


def _normalize_assumptions_ledger_content(raw: Any) -> dict[str, Any]:
    from lenses.blueprints_wizard.wizard_domain_normalize import normalize_assumption_ledger_entry

    if not isinstance(raw, dict):
        raw = {}
    entries_raw = raw.get("entries")
    entries: list[dict[str, Any]] = []
    if isinstance(entries_raw, list):
        for e in entries_raw[:256]:
            n = normalize_assumption_ledger_entry(e)
            if n is not None:
                entries.append(n)
    return {"entries": entries}


def _normalize_roadmap_content(raw: Any) -> dict[str, Any]:
    defaults: dict[str, Any] = {"summary": "", "themes": [], "horizons": [], "trace_refs": []}
    if not isinstance(raw, dict):
        return copy.deepcopy(defaults)
    out = {**defaults, **{k: v for k, v in raw.items() if k in defaults}}
    out["summary"] = _coerce_str(raw.get("summary"))[:24_000]
    themes: list[dict[str, Any]] = []
    tr = raw.get("themes")
    if isinstance(tr, list):
        for t in tr[:64]:
            if not isinstance(t, dict):
                continue
            title = _coerce_str(t.get("title"))[:500]
            desc = _coerce_str(t.get("description"))[:8_000]
            oc_raw = t.get("outcomes")
            outcomes: list[str] = []
            if isinstance(oc_raw, list):
                for o in oc_raw[:64]:
                    if isinstance(o, str):
                        s = o.strip()[:2_000]
                        if s:
                            outcomes.append(s)
            themes.append({"title": title, "description": desc, "outcomes": outcomes})
    out["themes"] = themes
    horizons: list[dict[str, Any]] = []
    hr = raw.get("horizons")
    if isinstance(hr, list):
        for h in hr[:32]:
            if not isinstance(h, dict):
                continue
            horizons.append(
                {
                    "label": _coerce_str(h.get("label"))[:500],
                    "notes": _coerce_str(h.get("notes"))[:8_000],
                }
            )
    out["horizons"] = horizons
    refs: list[str] = []
    rr = raw.get("trace_refs")
    if isinstance(rr, list):
        for x in rr[:MAX_TRACE_REFS]:
            if isinstance(x, str):
                s = x.strip()[:MAX_TRACE_REF_LEN]
                if s:
                    refs.append(s)
    out["trace_refs"] = refs
    return out


def _normalize_milestone_outline_content(raw: Any) -> dict[str, Any]:
    defaults: dict[str, Any] = {"milestones": [], "trace_refs": []}
    if not isinstance(raw, dict):
        return copy.deepcopy(defaults)
    out = {**defaults, **{k: v for k, v in raw.items() if k in defaults}}
    ms_raw = raw.get("milestones")
    milestones: list[dict[str, Any]] = []
    if isinstance(ms_raw, list):
        for m in ms_raw[:128]:
            if not isinstance(m, dict):
                continue
            mid = _coerce_str(m.get("id"))[:128] or _new_id()
            deps_raw = m.get("dependencies")
            deps: list[str] = []
            if isinstance(deps_raw, list):
                for d in deps_raw[:64]:
                    if isinstance(d, str) and d.strip():
                        deps.append(d.strip()[:200])
            sc = m.get("success_criteria")
            criteria = _coerce_str(sc)[:8_000] if sc is not None else ""
            milestones.append(
                {
                    "id": mid,
                    "title": _coerce_str(m.get("title"))[:500],
                    "target": _coerce_str(m.get("target"))[:2_000],
                    "dependencies": deps,
                    "success_criteria": criteria,
                    "notes": _coerce_str(m.get("notes"))[:8_000],
                }
            )
    out["milestones"] = milestones
    refs: list[str] = []
    rr = raw.get("trace_refs")
    if isinstance(rr, list):
        for x in rr[:MAX_TRACE_REFS]:
            if isinstance(x, str):
                s = x.strip()[:MAX_TRACE_REF_LEN]
                if s:
                    refs.append(s)
    out["trace_refs"] = refs
    return out


def _normalize_milestone_charters_content(raw: Any) -> dict[str, Any]:
    defaults: dict[str, Any] = {"charters": [], "trace_refs": []}
    if not isinstance(raw, dict):
        return copy.deepcopy(defaults)
    out = {**defaults, **{k: v for k, v in raw.items() if k in defaults}}
    ch_raw = raw.get("charters")
    charters: list[dict[str, Any]] = []
    if isinstance(ch_raw, list):
        for c in ch_raw[:128]:
            if not isinstance(c, dict):
                continue
            cid = _coerce_str(c.get("id"))[:128] or _new_id()
            charters.append(
                {
                    "id": cid,
                    "milestone_ref": _coerce_str(c.get("milestone_ref"))[:200],
                    "scope": _coerce_str(c.get("scope"))[:8_000],
                    "exit_criteria": _coerce_str(c.get("exit_criteria"))[:8_000],
                    "notes": _coerce_str(c.get("notes"))[:4_000],
                }
            )
    out["charters"] = charters
    refs: list[str] = []
    rr = raw.get("trace_refs")
    if isinstance(rr, list):
        for x in rr[:MAX_TRACE_REFS]:
            if isinstance(x, str):
                s = x.strip()[:MAX_TRACE_REF_LEN]
                if s:
                    refs.append(s)
    out["trace_refs"] = refs
    return out


def _normalize_wbe_tree_content(raw: Any) -> dict[str, Any]:
    defaults: dict[str, Any] = {"nodes": [], "trace_refs": []}
    if not isinstance(raw, dict):
        return copy.deepcopy(defaults)
    out = {**defaults, **{k: v for k, v in raw.items() if k in defaults}}
    nodes_raw = raw.get("nodes")
    nodes: list[dict[str, Any]] = []
    if isinstance(nodes_raw, list):
        for n in nodes_raw[:512]:
            if not isinstance(n, dict):
                continue
            nid = _coerce_str(n.get("id"))[:128] or _new_id()
            est = n.get("estimate")
            est_s = _coerce_str(est)[:64] if est is not None else ""
            pid = n.get("parent_id")
            parent_id = _coerce_str(pid)[:128] if pid is not None else ""
            nodes.append(
                {
                    "id": nid,
                    "title": _coerce_str(n.get("title"))[:500],
                    "parent_id": parent_id,
                    "estimate": est_s,
                    "notes": _coerce_str(n.get("notes"))[:4_000],
                }
            )
    out["nodes"] = nodes
    refs: list[str] = []
    rr = raw.get("trace_refs")
    if isinstance(rr, list):
        for x in rr[:MAX_TRACE_REFS]:
            if isinstance(x, str):
                s = x.strip()[:MAX_TRACE_REF_LEN]
                if s:
                    refs.append(s)
    out["trace_refs"] = refs
    return out


def _normalize_dependency_map_content(raw: Any) -> dict[str, Any]:
    defaults: dict[str, Any] = {"edges": [], "trace_refs": []}
    if not isinstance(raw, dict):
        return copy.deepcopy(defaults)
    out = {**defaults, **{k: v for k, v in raw.items() if k in defaults}}
    edges_raw = raw.get("edges")
    edges: list[dict[str, Any]] = []
    if isinstance(edges_raw, list):
        for e in edges_raw[:256]:
            if not isinstance(e, dict):
                continue
            edges.append(
                {
                    "from_ref": _coerce_str(e.get("from_ref"))[:200],
                    "to_ref": _coerce_str(e.get("to_ref"))[:200],
                    "dep_type": _coerce_str(e.get("dep_type"))[:120],
                    "team": _coerce_str(e.get("team"))[:200],
                    "notes": _coerce_str(e.get("notes"))[:2_000],
                }
            )
    out["edges"] = edges
    refs: list[str] = []
    rr = raw.get("trace_refs")
    if isinstance(rr, list):
        for x in rr[:MAX_TRACE_REFS]:
            if isinstance(x, str):
                s = x.strip()[:MAX_TRACE_REF_LEN]
                if s:
                    refs.append(s)
    out["trace_refs"] = refs
    return out


def _normalize_prd_content(raw: Any) -> dict[str, Any]:
    defaults: dict[str, Any] = {
        "summary": "",
        "goals": "",
        "personas": "",
        "scope_in": "",
        "scope_out": "",
        "user_stories": [],
        "trace_refs": [],
    }
    if not isinstance(raw, dict):
        return copy.deepcopy(defaults)
    out = {**defaults, **{k: v for k, v in raw.items() if k in defaults}}
    out["summary"] = _coerce_str(raw.get("summary"))[:24_000]
    out["goals"] = _coerce_str(raw.get("goals"))[:16_000]
    out["personas"] = _coerce_str(raw.get("personas"))[:16_000]
    out["scope_in"] = _coerce_str(raw.get("scope_in"))[:8_000]
    out["scope_out"] = _coerce_str(raw.get("scope_out"))[:8_000]
    stories: list[str] = []
    us = raw.get("user_stories")
    if isinstance(us, list):
        for s in us[:128]:
            if isinstance(s, str):
                t = s.strip()[:4_000]
                if t:
                    stories.append(t)
    out["user_stories"] = stories
    refs: list[str] = []
    rr = raw.get("trace_refs")
    if isinstance(rr, list):
        for x in rr[:MAX_TRACE_REFS]:
            if isinstance(x, str):
                s = x.strip()[:MAX_TRACE_REF_LEN]
                if s:
                    refs.append(s)
    out["trace_refs"] = refs
    return out


def _normalize_architecture_brief_content(raw: Any) -> dict[str, Any]:
    defaults: dict[str, Any] = {
        "context": "",
        "containers": "",
        "components": [],
        "interfaces": [],
        "risks": "",
        "trace_refs": [],
    }
    if not isinstance(raw, dict):
        return copy.deepcopy(defaults)
    out = {**defaults, **{k: v for k, v in raw.items() if k in defaults}}
    out["context"] = _coerce_str(raw.get("context"))[:16_000]
    out["containers"] = _coerce_str(raw.get("containers"))[:16_000]
    out["risks"] = _coerce_str(raw.get("risks"))[:8_000]
    comps: list[str] = []
    cr = raw.get("components")
    if isinstance(cr, list):
        for c in cr[:64]:
            if isinstance(c, str):
                t = c.strip()[:4_000]
                if t:
                    comps.append(t)
    out["components"] = comps
    interfaces: list[dict[str, Any]] = []
    ir = raw.get("interfaces")
    if isinstance(ir, list):
        for item in ir[:64]:
            if not isinstance(item, dict):
                continue
            interfaces.append(
                {
                    "name": _coerce_str(item.get("name"))[:300],
                    "contract": _coerce_str(item.get("contract"))[:4_000],
                }
            )
    out["interfaces"] = interfaces
    refs: list[str] = []
    rr = raw.get("trace_refs")
    if isinstance(rr, list):
        for x in rr[:MAX_TRACE_REFS]:
            if isinstance(x, str):
                s = x.strip()[:MAX_TRACE_REF_LEN]
                if s:
                    refs.append(s)
    out["trace_refs"] = refs
    return out


def _normalize_nfr_checklist_content(raw: Any) -> dict[str, Any]:
    defaults: dict[str, Any] = {"rows": [], "policy_notes": [], "trace_refs": []}
    if not isinstance(raw, dict):
        return copy.deepcopy(defaults)
    out = {**defaults, **{k: v for k, v in raw.items() if k in defaults}}
    rows_raw = raw.get("rows")
    rows: list[dict[str, Any]] = []
    if isinstance(rows_raw, list):
        for r in rows_raw[:128]:
            if not isinstance(r, dict):
                continue
            rows.append(
                {
                    "category": _coerce_str(r.get("category"))[:200],
                    "requirement": _coerce_str(r.get("requirement"))[:4_000],
                    "measure": _coerce_str(r.get("measure"))[:2_000],
                    "status": _coerce_str(r.get("status"))[:120],
                }
            )
    out["rows"] = rows
    pn_raw = raw.get("policy_notes")
    policy_notes: list[str] = []
    if isinstance(pn_raw, list):
        for p in pn_raw[:MAX_POLICY_NOTES]:
            if isinstance(p, str):
                t = p.strip()[:2_000]
                if t:
                    policy_notes.append(t)
    out["policy_notes"] = policy_notes
    refs: list[str] = []
    rr = raw.get("trace_refs")
    if isinstance(rr, list):
        for x in rr[:MAX_TRACE_REFS]:
            if isinstance(x, str):
                s = x.strip()[:MAX_TRACE_REF_LEN]
                if s:
                    refs.append(s)
    out["trace_refs"] = refs
    return out


def _normalize_adr_seeds_content(raw: Any) -> dict[str, Any]:
    defaults: dict[str, Any] = {"decisions": [], "trace_refs": []}
    if not isinstance(raw, dict):
        return copy.deepcopy(defaults)
    out = {**defaults, **{k: v for k, v in raw.items() if k in defaults}}
    dec_raw = raw.get("decisions")
    decisions: list[dict[str, Any]] = []
    if isinstance(dec_raw, list):
        for d in dec_raw[:64]:
            if not isinstance(d, dict):
                continue
            did = _coerce_str(d.get("id"))[:128] or _new_id()
            decisions.append(
                {
                    "id": did,
                    "title": _coerce_str(d.get("title"))[:500],
                    "context": _coerce_str(d.get("context"))[:8_000],
                    "options": _coerce_str(d.get("options"))[:8_000],
                    "decision_stub": _coerce_str(d.get("decision_stub"))[:4_000],
                }
            )
    out["decisions"] = decisions
    refs: list[str] = []
    rr = raw.get("trace_refs")
    if isinstance(rr, list):
        for x in rr[:MAX_TRACE_REFS]:
            if isinstance(x, str):
                s = x.strip()[:MAX_TRACE_REF_LEN]
                if s:
                    refs.append(s)
    out["trace_refs"] = refs
    return out


def _normalize_ownership_review_matrix_content(raw: Any) -> dict[str, Any]:
    defaults: dict[str, Any] = {"rows": [], "policy_notes": [], "trace_refs": []}
    if not isinstance(raw, dict):
        return copy.deepcopy(defaults)
    out = {**defaults, **{k: v for k, v in raw.items() if k in defaults}}
    rows_raw = raw.get("rows")
    rows: list[dict[str, Any]] = []
    if isinstance(rows_raw, list):
        for r in rows_raw[:128]:
            if not isinstance(r, dict):
                continue
            rows.append(
                {
                    "area": _coerce_str(r.get("area"))[:500],
                    "owner": _coerce_str(r.get("owner"))[:300],
                    "reviewer": _coerce_str(r.get("reviewer"))[:300],
                    "raci": _coerce_str(r.get("raci"))[:500],
                    "handoff_notes": _coerce_str(r.get("handoff_notes"))[:4_000],
                    "policy_placeholder": _coerce_str(r.get("policy_placeholder"))[:2_000],
                }
            )
    out["rows"] = rows
    pn_raw = raw.get("policy_notes")
    policy_notes: list[str] = []
    if isinstance(pn_raw, list):
        for p in pn_raw[:MAX_POLICY_NOTES]:
            if isinstance(p, str):
                t = p.strip()[:2_000]
                if t:
                    policy_notes.append(t)
    out["policy_notes"] = policy_notes
    refs: list[str] = []
    rr = raw.get("trace_refs")
    if isinstance(rr, list):
        for x in rr[:MAX_TRACE_REFS]:
            if isinstance(x, str):
                s = x.strip()[:MAX_TRACE_REF_LEN]
                if s:
                    refs.append(s)
    out["trace_refs"] = refs
    return out


def _normalize_upstream_artifact_ref(raw: Any) -> dict[str, Any]:
    if not isinstance(raw, dict):
        return {
            "artifact_key": "",
            "generation_id": "",
            "wbe_node_id": "",
            "story_id": "",
            "spark_id": "",
        }
    return {
        "artifact_key": _coerce_str(raw.get("artifact_key"))[:64],
        "generation_id": _coerce_str(raw.get("generation_id"))[:128],
        "wbe_node_id": _coerce_str(raw.get("wbe_node_id"))[:128],
        "story_id": _coerce_str(raw.get("story_id"))[:128],
        "spark_id": _coerce_str(raw.get("spark_id"))[:128],
    }


def _normalize_sparks_plan_content(raw: Any) -> dict[str, Any]:
    defaults: dict[str, Any] = {"sparks": [], "trace_refs": []}
    if not isinstance(raw, dict):
        return copy.deepcopy(defaults)
    out = {**defaults, **{k: v for k, v in raw.items() if k in defaults}}
    sparks_raw = raw.get("sparks")
    sparks: list[dict[str, Any]] = []
    if isinstance(sparks_raw, list):
        for s in sparks_raw[:MAX_SPARK_ROWS]:
            if not isinstance(s, dict):
                continue
            sid = _coerce_str(s.get("spark_id"))[:128] or _new_id()
            sparks.append(
                {
                    "spark_id": sid,
                    "story_ref": _coerce_str(s.get("story_ref"))[:200],
                    "phase_prefix": _coerce_str(s.get("phase_prefix"))[:64],
                    "intent": _coerce_str(s.get("intent"))[:4_000],
                    "status": _coerce_str(s.get("status"))[:120],
                    "notes": _coerce_str(s.get("notes"))[:4_000],
                }
            )
    out["sparks"] = sparks
    refs: list[str] = []
    rr = raw.get("trace_refs")
    if isinstance(rr, list):
        for x in rr[:MAX_TRACE_REFS]:
            if isinstance(x, str):
                t = x.strip()[:MAX_TRACE_REF_LEN]
                if t:
                    refs.append(t)
    out["trace_refs"] = refs
    return out


def _normalize_charge_plan_content(raw: Any) -> dict[str, Any]:
    defaults: dict[str, Any] = {"charges": [], "iteration_note": "", "trace_refs": []}
    if not isinstance(raw, dict):
        return copy.deepcopy(defaults)
    out = {**defaults, **{k: v for k, v in raw.items() if k in defaults}}
    out["iteration_note"] = _coerce_str(raw.get("iteration_note"))[:4_000]
    ch_raw = raw.get("charges")
    charges: list[dict[str, Any]] = []
    if isinstance(ch_raw, list):
        for c in ch_raw[:MAX_CHARGE_ROWS]:
            if not isinstance(c, dict):
                continue
            cid = _coerce_str(c.get("charge_id"))[:128] or _new_id()
            sr = c.get("spark_refs")
            spark_refs: list[str] = []
            if isinstance(sr, list):
                for x in sr[:64]:
                    if isinstance(x, str) and x.strip():
                        spark_refs.append(x.strip()[:128])
            charges.append(
                {
                    "charge_id": cid,
                    "spark_refs": spark_refs,
                    "owner": _coerce_str(c.get("owner"))[:300],
                    "energy": _coerce_str(c.get("energy"))[:120],
                    "notes": _coerce_str(c.get("notes"))[:4_000],
                }
            )
    out["charges"] = charges
    refs: list[str] = []
    rr = raw.get("trace_refs")
    if isinstance(rr, list):
        for x in rr[:MAX_TRACE_REFS]:
            if isinstance(x, str):
                t = x.strip()[:MAX_TRACE_REF_LEN]
                if t:
                    refs.append(t)
    out["trace_refs"] = refs
    return out


def _normalize_implementation_tasklets_content(raw: Any) -> dict[str, Any]:
    defaults: dict[str, Any] = {"tasklets": [], "trace_refs": []}
    if not isinstance(raw, dict):
        return copy.deepcopy(defaults)
    out = {**defaults, **{k: v for k, v in raw.items() if k in defaults}}
    tr_raw = raw.get("tasklets")
    tasklets: list[dict[str, Any]] = []
    if isinstance(tr_raw, list):
        for t in tr_raw[:MAX_TASKLET_ROWS]:
            if not isinstance(t, dict):
                continue
            tid = _coerce_str(t.get("id"))[:128] or _new_id()
            up_raw = t.get("upstream_artifacts")
            upstream: list[dict[str, Any]] = []
            if isinstance(up_raw, list):
                for u in up_raw[:MAX_UPSTREAM_REFS]:
                    upstream.append(_normalize_upstream_artifact_ref(u))
            tasklets.append(
                {
                    "id": tid,
                    "title": _coerce_str(t.get("title"))[:500],
                    "detail": _coerce_str(t.get("detail"))[:8_000],
                    "estimate": _coerce_str(t.get("estimate"))[:64],
                    "notes": _coerce_str(t.get("notes"))[:4_000],
                    "upstream_artifacts": upstream,
                }
            )
    out["tasklets"] = tasklets
    refs: list[str] = []
    rr = raw.get("trace_refs")
    if isinstance(rr, list):
        for x in rr[:MAX_TRACE_REFS]:
            if isinstance(x, str):
                s = x.strip()[:MAX_TRACE_REF_LEN]
                if s:
                    refs.append(s)
    out["trace_refs"] = refs
    return out


def _normalize_acceptance_criteria_content(raw: Any) -> dict[str, Any]:
    defaults: dict[str, Any] = {"criteria": [], "trace_refs": []}
    if not isinstance(raw, dict):
        return copy.deepcopy(defaults)
    out = {**defaults, **{k: v for k, v in raw.items() if k in defaults}}
    cr_raw = raw.get("criteria")
    criteria: list[dict[str, Any]] = []
    if isinstance(cr_raw, list):
        for c in cr_raw[:MAX_ACCEPTANCE_ROWS]:
            if not isinstance(c, dict):
                continue
            cid = _coerce_str(c.get("id"))[:128] or _new_id()
            tr = c.get("trace_refs")
            row_refs: list[str] = []
            if isinstance(tr, list):
                for x in tr[:32]:
                    if isinstance(x, str) and x.strip():
                        row_refs.append(x.strip()[:MAX_TRACE_REF_LEN])
            criteria.append(
                {
                    "id": cid,
                    "statement": _coerce_str(c.get("statement"))[:8_000],
                    "tasklet_id": _coerce_str(c.get("tasklet_id"))[:128],
                    "story_ref": _coerce_str(c.get("story_ref"))[:200],
                    "trace_refs": row_refs,
                }
            )
    out["criteria"] = criteria
    refs: list[str] = []
    rr = raw.get("trace_refs")
    if isinstance(rr, list):
        for x in rr[:MAX_TRACE_REFS]:
            if isinstance(x, str):
                s = x.strip()[:MAX_TRACE_REF_LEN]
                if s:
                    refs.append(s)
    out["trace_refs"] = refs
    return out


def _normalize_execution_dependency_sequence_content(raw: Any) -> dict[str, Any]:
    defaults: dict[str, Any] = {"ordered_steps": [], "trace_refs": []}
    if not isinstance(raw, dict):
        return copy.deepcopy(defaults)
    out = {**defaults, **{k: v for k, v in raw.items() if k in defaults}}
    st_raw = raw.get("ordered_steps")
    steps: list[dict[str, Any]] = []
    if isinstance(st_raw, list):
        for s in st_raw[:MAX_EXEC_SEQUENCE_STEPS]:
            if not isinstance(s, dict):
                continue
            sid = _coerce_str(s.get("step_id"))[:128] or _new_id()
            seq_v = s.get("seq")
            try:
                seq_n = int(seq_v) if seq_v is not None else 0
            except (TypeError, ValueError):
                seq_n = 0
            steps.append(
                {
                    "step_id": sid,
                    "seq": seq_n,
                    "ref_type": _coerce_str(s.get("ref_type"))[:64],
                    "ref_id": _coerce_str(s.get("ref_id"))[:200],
                    "notes": _coerce_str(s.get("notes"))[:4_000],
                }
            )
    out["ordered_steps"] = steps
    refs: list[str] = []
    rr = raw.get("trace_refs")
    if isinstance(rr, list):
        for x in rr[:MAX_TRACE_REFS]:
            if isinstance(x, str):
                t = x.strip()[:MAX_TRACE_REF_LEN]
                if t:
                    refs.append(t)
    out["trace_refs"] = refs
    return out


def _normalize_qa_verification_checklist_content(raw: Any) -> dict[str, Any]:
    defaults: dict[str, Any] = {"items": [], "trace_refs": []}
    if not isinstance(raw, dict):
        return copy.deepcopy(defaults)
    out = {**defaults, **{k: v for k, v in raw.items() if k in defaults}}
    it_raw = raw.get("items")
    items: list[dict[str, Any]] = []
    if isinstance(it_raw, list):
        for it in it_raw[:MAX_QA_CHECKLIST_ITEMS]:
            if not isinstance(it, dict):
                continue
            iid = _coerce_str(it.get("id"))[:128] or _new_id()
            items.append(
                {
                    "id": iid,
                    "check": _coerce_str(it.get("check"))[:8_000],
                    "evidence": _coerce_str(it.get("evidence"))[:4_000],
                    "tasklet_id": _coerce_str(it.get("tasklet_id"))[:128],
                }
            )
    out["items"] = items
    refs: list[str] = []
    rr = raw.get("trace_refs")
    if isinstance(rr, list):
        for x in rr[:MAX_TRACE_REFS]:
            if isinstance(x, str):
                t = x.strip()[:MAX_TRACE_REF_LEN]
                if t:
                    refs.append(t)
    out["trace_refs"] = refs
    return out


def _normalize_rollout_notes_content(raw: Any) -> dict[str, Any]:
    defaults: dict[str, Any] = {"sections": [], "canary_notes": "", "trace_refs": []}
    if not isinstance(raw, dict):
        return copy.deepcopy(defaults)
    out = {**defaults, **{k: v for k, v in raw.items() if k in defaults}}
    out["canary_notes"] = _coerce_str(raw.get("canary_notes"))[:8_000]
    sec_raw = raw.get("sections")
    sections: list[dict[str, Any]] = []
    if isinstance(sec_raw, list):
        for sec in sec_raw[:MAX_ROLLOUT_SECTIONS]:
            if not isinstance(sec, dict):
                continue
            sections.append(
                {
                    "title": _coerce_str(sec.get("title"))[:500],
                    "body": _coerce_str(sec.get("body"))[:24_000],
                }
            )
    out["sections"] = sections
    refs: list[str] = []
    rr = raw.get("trace_refs")
    if isinstance(rr, list):
        for x in rr[:MAX_TRACE_REFS]:
            if isinstance(x, str):
                t = x.strip()[:MAX_TRACE_REF_LEN]
                if t:
                    refs.append(t)
    out["trace_refs"] = refs
    return out


def implementation_tasklets_traceability_ok(content: dict[str, Any]) -> bool:
    """Every tasklet must list at least one upstream artifact_key (approved-artifact trace)."""
    tasklets = content.get("tasklets")
    if not isinstance(tasklets, list) or len(tasklets) == 0:
        return False
    for t in tasklets:
        if not isinstance(t, dict):
            return False
        ups = t.get("upstream_artifacts")
        if not isinstance(ups, list) or len(ups) == 0:
            return False
        ok_row = False
        for u in ups:
            if not isinstance(u, dict):
                continue
            ak = _coerce_str(u.get("artifact_key"))[:64]
            if ak:
                ok_row = True
                break
        if not ok_row:
            return False
    return True


_CONTENT_NORMALIZERS = {
    "foundation_brief_final": _normalize_fb_final_content,
    "assumptions_ledger": _normalize_assumptions_ledger_content,
    "roadmap": _normalize_roadmap_content,
    "milestone_outline": _normalize_milestone_outline_content,
    "milestone_charters": _normalize_milestone_charters_content,
    "wbe_tree": _normalize_wbe_tree_content,
    "dependency_map": _normalize_dependency_map_content,
    "prd": _normalize_prd_content,
    "architecture_brief": _normalize_architecture_brief_content,
    "nfr_checklist": _normalize_nfr_checklist_content,
    "adr_seeds": _normalize_adr_seeds_content,
    "ownership_review_matrix": _normalize_ownership_review_matrix_content,
    "sparks_plan": _normalize_sparks_plan_content,
    "charge_plan": _normalize_charge_plan_content,
    "implementation_tasklets": _normalize_implementation_tasklets_content,
    "acceptance_criteria": _normalize_acceptance_criteria_content,
    "execution_dependency_sequence": _normalize_execution_dependency_sequence_content,
    "qa_verification_checklist": _normalize_qa_verification_checklist_content,
    "rollout_notes": _normalize_rollout_notes_content,
}


def normalize_artifact_record_content(artifact_key: str, raw: Any) -> dict[str, Any]:
    fn = _CONTENT_NORMALIZERS.get(artifact_key)
    if fn is None:
        return {}
    return fn(raw)


def normalize_single_artifact_record(artifact_key: str, raw: Any) -> dict[str, Any] | None:
    """One envelope: content, quality, review_status, locked, feedback, provenance."""
    if not isinstance(raw, dict):
        return None
    content = normalize_artifact_record_content(artifact_key, raw.get("content"))
    quality = normalize_quality_rubric(raw.get("quality"))
    review_status = coerce_artifact_review_status(raw.get("review_status"))
    locked = raw.get("locked")
    lb = locked if isinstance(locked, bool) else False
    feedback = _coerce_str(raw.get("feedback"))[:8_000]
    prov = normalize_provenance(raw.get("provenance"))
    if lb:
        review_status = "locked"
    return {
        "content": content,
        "quality": quality,
        "review_status": review_status,
        "locked": lb,
        "feedback": feedback,
        "provenance": prov,
    }


def normalize_artifact_generation_artifacts_map(raw: Any) -> dict[str, Any]:
    out: dict[str, Any] = {}
    if not isinstance(raw, dict):
        return out
    for key in ARTIFACT_SLICE_KEYS:
        if key not in raw:
            continue
        rec = normalize_single_artifact_record(key, raw.get(key))
        if rec is not None:
            out[key] = rec
    return out


def normalize_artifact_generation(raw: Any) -> dict[str, Any]:
    defaults = {
        "schema_version": ARTIFACT_GENERATION_SCHEMA_VERSION,
        "artifacts": {},
    }
    if not isinstance(raw, dict):
        return copy.deepcopy(defaults)
    out = {**defaults, **{k: v for k, v in raw.items() if k in defaults}}
    sv = raw.get("schema_version")
    if isinstance(sv, int) and not isinstance(sv, bool):
        out["schema_version"] = max(1, min(99, sv))
    elif isinstance(sv, str) and sv.isdigit():
        out["schema_version"] = max(1, min(99, int(sv)))
    else:
        out["schema_version"] = ARTIFACT_GENERATION_SCHEMA_VERSION
    out["artifacts"] = normalize_artifact_generation_artifacts_map(raw.get("artifacts"))
    return out


def empty_artifact_generation() -> dict[str, Any]:
    return normalize_artifact_generation({})


def merge_artifact_generation_bundle(
    existing: dict[str, Any] | None,
    incoming_artifacts: dict[str, Any],
    *,
    replace_keys: frozenset[str] | None = None,
) -> dict[str, Any]:
    """
    Deep-merge incoming artifact records into existing bundle.
    If replace_keys is None, replace all provided keys entirely with normalized incoming.
    If replace_keys is set, only those keys are replaced; others unchanged.
    """
    base = normalize_artifact_generation(existing)
    art = dict(base.get("artifacts") or {})
    for key, rec in incoming_artifacts.items():
        if key not in ARTIFACT_SLICE_KEYS:
            continue
        if not isinstance(rec, dict):
            continue
        normalized = normalize_single_artifact_record(key, rec)
        if normalized is None:
            continue
        if replace_keys is not None and key not in replace_keys:
            continue
        prev = art.get(key)
        if isinstance(prev, dict) and prev.get("locked") is True:
            continue
        art[key] = normalized
    base["artifacts"] = art
    return base
