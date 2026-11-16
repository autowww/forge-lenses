"""Normalize ``payload.wizard_domain`` (schema v1). Pure dict in/out; preserves unknown top-level keys."""

from __future__ import annotations

import copy
from typing import Any

from lenses.blueprints_wizard.artifact_generation_normalize import normalize_artifact_generation
from lenses.blueprints_wizard.domain_enums import (
    coerce_artifact_status,
    coerce_assumption_ledger_status,
    coerce_autonomy_level,
    coerce_contribution_setup_kind,
    coerce_context_source,
    coerce_interpretation_field_status,
    coerce_mission_type,
    coerce_mutation_policy,
    coerce_prompt_intent,
    coerce_prompt_mode,
    coerce_scope_boundary,
    coerce_target_stage,
    normalize_closure_options_list,
)


def _coerce_str(v: Any) -> str:
    if v is None:
        return ""
    return str(v).strip()


def _coerce_opt_str(v: Any) -> str | None:
    if v is None:
        return None
    s = str(v).strip()
    return s if s else None


def _new_entry_id() -> str:
    import secrets

    return secrets.token_urlsafe(8)


def _coerce_schema_version(raw: Any) -> int:
    if isinstance(raw, int) and not isinstance(raw, bool):
        return max(1, raw)
    if isinstance(raw, str) and raw.isdigit():
        return max(1, int(raw))
    return 1


def normalize_foundation_brief(raw: Any) -> dict[str, Any]:
    defaults = {"markdown": "", "field_statuses": {}}
    if not isinstance(raw, dict):
        return dict(defaults)
    out = dict(defaults)
    out["markdown"] = _coerce_str(raw.get("markdown"))[:120_000]
    fs = raw.get("field_statuses")
    statuses: dict[str, str] = {}
    if isinstance(fs, dict):
        for key, val in fs.items():
            k = _coerce_str(key)[:200]
            if not k:
                continue
            statuses[k] = coerce_interpretation_field_status(val)
    out["field_statuses"] = statuses
    return out


def normalize_assumption_ledger_entry(raw: Any) -> dict[str, Any] | None:
    if not isinstance(raw, dict):
        return None
    eid = _coerce_str(raw.get("id"))
    if not eid:
        eid = _new_entry_id()
    text = _coerce_str(raw.get("text"))[:16_000]
    src = raw.get("source")
    if src is None or (isinstance(src, str) and not src.strip()):
        source = None
    else:
        source = coerce_context_source(src)
    created_at = raw.get("created_at")
    ca = _coerce_str(created_at)[:64] if created_at is not None else ""
    status = coerce_assumption_ledger_status(raw.get("status"))
    return {
        "id": eid[:128],
        "text": text,
        "source": source,
        "created_at": ca,
        "status": status,
    }


def normalize_assumption_ledger(raw: Any) -> list[dict[str, Any]]:
    if not isinstance(raw, list):
        return []
    out: list[dict[str, Any]] = []
    for item in raw:
        n = normalize_assumption_ledger_entry(item)
        if n is not None:
            out.append(n)
    return out


def normalize_artifact_pack_item(raw: Any) -> dict[str, Any] | None:
    if not isinstance(raw, dict):
        return None
    iid = _coerce_str(raw.get("id")) or _new_entry_id()
    label = _coerce_str(raw.get("label"))[:500]
    status = coerce_artifact_status(raw.get("status"))
    return {"id": iid[:128], "label": label, "status": status}


def normalize_artifact_pack(raw: Any) -> dict[str, Any]:
    defaults = {"id": "", "label": "", "items": []}
    if not isinstance(raw, dict):
        return dict(defaults)
    out = {**defaults, **{k: v for k, v in raw.items() if k != "items"}}
    out["id"] = _coerce_str(raw.get("id"))[:128] or _new_entry_id()
    out["label"] = _coerce_str(raw.get("label"))[:500]
    items_raw = raw.get("items")
    items: list[dict[str, Any]] = []
    if isinstance(items_raw, list):
        for it in items_raw:
            n = normalize_artifact_pack_item(it)
            if n is not None:
                items.append(n)
    out["items"] = items
    return out


def normalize_scope_spec(raw: Any) -> dict[str, Any]:
    """Wizard scope narrative + optional path mirrors (``payload.scope`` remains authoritative for validation)."""
    defaults = {
        "summary": "",
        "constraints_note": "",
        "wbs_rel": None,
        "roadmap_rel": None,
        "roadmap_section_id": None,
        "scope_boundary": "full_plan",
        "milestone_ref": "",
        "wbe_path": "",
        "capability_label": "",
        "team_label": "",
        "repo_paths": [],
        "recheck_issue_refs": "",
        "closure_options": [],
    }
    if not isinstance(raw, dict):
        return dict(defaults)
    out = dict(defaults)
    out["summary"] = _coerce_str(raw.get("summary"))[:8000]
    out["constraints_note"] = _coerce_str(raw.get("constraints_note"))[:8000]
    out["wbs_rel"] = _coerce_opt_str(raw.get("wbs_rel"))
    out["roadmap_rel"] = _coerce_opt_str(raw.get("roadmap_rel"))
    sid = raw.get("roadmap_section_id")
    out["roadmap_section_id"] = _coerce_opt_str(sid) if sid is not None else None
    out["scope_boundary"] = coerce_scope_boundary(raw.get("scope_boundary"))
    out["milestone_ref"] = _coerce_str(raw.get("milestone_ref"))[:2000]
    out["wbe_path"] = _coerce_str(raw.get("wbe_path"))[:4000]
    out["capability_label"] = _coerce_str(raw.get("capability_label"))[:2000]
    out["team_label"] = _coerce_str(raw.get("team_label"))[:2000]
    out["recheck_issue_refs"] = _coerce_str(raw.get("recheck_issue_refs"))[:8000]
    rp_raw = raw.get("repo_paths")
    repo_paths: list[str] = []
    if isinstance(rp_raw, list):
        for p in rp_raw:
            if isinstance(p, str):
                s = p.strip()[:2000]
                if s:
                    repo_paths.append(s)
    out["repo_paths"] = repo_paths
    out["closure_options"] = normalize_closure_options_list(raw.get("closure_options"))
    return out


def normalize_run_plan_step(raw: Any) -> dict[str, Any] | None:
    if not isinstance(raw, dict):
        return None
    sid = _coerce_str(raw.get("id")) or _new_entry_id()
    return {
        "id": sid[:128],
        "title": _coerce_str(raw.get("title"))[:500],
        "detail": _coerce_str(raw.get("detail"))[:8000],
    }


def normalize_run_plan(raw: Any) -> dict[str, Any]:
    defaults = {"id": "", "title": "", "steps": []}
    if not isinstance(raw, dict):
        return dict(defaults)
    out = {**defaults, **{k: v for k, v in raw.items() if k != "steps"}}
    out["id"] = _coerce_str(raw.get("id"))[:128] or _new_entry_id()
    out["title"] = _coerce_str(raw.get("title"))[:500]
    steps_raw = raw.get("steps")
    steps: list[dict[str, Any]] = []
    if isinstance(steps_raw, list):
        for s in steps_raw:
            n = normalize_run_plan_step(s)
            if n is not None:
                steps.append(n)
    out["steps"] = steps
    return out


def normalize_review_gate(raw: Any) -> dict[str, Any] | None:
    if not isinstance(raw, dict):
        return None
    gid = _coerce_str(raw.get("id")) or _new_entry_id()
    passed = raw.get("passed")
    pb = passed if isinstance(passed, bool) else False
    return {
        "id": gid[:128],
        "title": _coerce_str(raw.get("title"))[:500],
        "passed": pb,
        "notes": _coerce_str(raw.get("notes"))[:8000],
    }


_RECHECK_PRIMARY_LABELS = frozenset(
    ("missing", "blocked", "conflicting", "stale", "draft", "approved", "present")
)


def normalize_recheck_report(raw: Any) -> dict[str, Any]:
    """Normalize ``recheck_summary.report`` (schema v1)."""
    empty_rec: dict[str, Any] = {
        "schema_version": 1,
        "computed_at": "",
        "artifacts": [],
        "buckets": [],
        "recommendations": {
            "regenerate_keys": [],
            "approve_first": [],
            "unlock_or_request_changes": [],
            "flag_for_review": [],
        },
    }
    if not isinstance(raw, dict):
        return dict(empty_rec)
    try:
        sv = int(raw.get("schema_version") or 1)
    except (TypeError, ValueError):
        sv = 1
    out: dict[str, Any] = {
        "schema_version": max(1, min(sv, 99)),
        "computed_at": _coerce_str(raw.get("computed_at"))[:64],
        "artifacts": [],
        "buckets": [],
        "recommendations": dict(empty_rec["recommendations"]),
    }
    arts_raw = raw.get("artifacts")
    if isinstance(arts_raw, list):
        for row in arts_raw[:128]:
            if not isinstance(row, dict):
                continue
            pl = _coerce_str(row.get("primary_label"))[:32]
            if pl not in _RECHECK_PRIMARY_LABELS:
                pl = "missing"
            reasons: list[str] = []
            rr = row.get("reasons")
            if isinstance(rr, list):
                for x in rr[:32]:
                    if isinstance(x, str):
                        t = x.strip()[:2000]
                        if t:
                            reasons.append(t)
            out["artifacts"].append(
                {
                    "artifact_key": _coerce_str(row.get("artifact_key"))[:128],
                    "primary_label": pl,
                    "reasons": reasons,
                    "review_status": _coerce_str(row.get("review_status"))[:64],
                    "generation_id": _coerce_str(row.get("generation_id"))[:128],
                    "created_at": _coerce_str(row.get("created_at"))[:64],
                    "parent_generation_id": _coerce_str(row.get("parent_generation_id"))[:128],
                }
            )
    buckets_raw = raw.get("buckets")
    if isinstance(buckets_raw, list):
        for b in buckets_raw[:8]:
            if not isinstance(b, dict):
                continue
            bid = _coerce_str(b.get("id"))[:32]
            wl = _coerce_str(b.get("worst_label"))[:32]
            if wl not in _RECHECK_PRIMARY_LABELS:
                wl = "present"
            keys: list[str] = []
            kr = b.get("artifact_keys")
            if isinstance(kr, list):
                for x in kr[:64]:
                    if isinstance(x, str):
                        s = x.strip()[:128]
                        if s:
                            keys.append(s)
            out["buckets"].append({"id": bid, "worst_label": wl, "artifact_keys": keys})
    rec = raw.get("recommendations")
    if isinstance(rec, dict):
        for fld in ("regenerate_keys", "approve_first", "unlock_or_request_changes"):
            lst = rec.get(fld)
            if isinstance(lst, list):
                acc: list[str] = []
                for x in lst[:64]:
                    if isinstance(x, str):
                        s = x.strip()[:128]
                        if s:
                            acc.append(s)
                out["recommendations"][fld] = acc
        fr = rec.get("flag_for_review")
        if isinstance(fr, list):
            notes: list[str] = []
            for x in fr[:64]:
                if isinstance(x, str):
                    t = x.strip()[:4000]
                    if t:
                        notes.append(t)
            out["recommendations"]["flag_for_review"] = notes
    return out


def normalize_review_gates(raw: Any) -> list[dict[str, Any]]:
    if not isinstance(raw, list):
        return []
    out: list[dict[str, Any]] = []
    for g in raw:
        n = normalize_review_gate(g)
        if n is not None:
            out.append(n)
    return out


def normalize_recheck_summary(raw: Any) -> dict[str, Any]:
    defaults = {"checked_at": "", "passed": False, "issues": []}
    if not isinstance(raw, dict):
        return {**defaults, "report": normalize_recheck_report({})}
    out = {**defaults, **{k: v for k, v in raw.items() if k not in ("issues", "report")}}
    out["checked_at"] = _coerce_str(raw.get("checked_at"))[:64]
    p = raw.get("passed")
    out["passed"] = p if isinstance(p, bool) else False
    issues_raw = raw.get("issues")
    issues: list[str] = []
    if isinstance(issues_raw, list):
        for x in issues_raw:
            if isinstance(x, str):
                t = x.strip()[:2000]
                if t:
                    issues.append(t)
    out["issues"] = issues
    out["report"] = normalize_recheck_report(raw.get("report"))
    return out


def normalize_build_pack_plan(raw: Any) -> dict[str, Any]:
    defaults = {
        "format": "json",
        "paths": [],
        "notes": "",
        "allowed_write_globs": [],
        "guardrail_notes": "",
    }
    if not isinstance(raw, dict):
        return dict(defaults)
    out = {**defaults, **{k: v for k, v in raw.items() if k not in ("paths", "allowed_write_globs")}}
    out["format"] = _coerce_str(raw.get("format"))[:64] or "json"
    out["notes"] = _coerce_str(raw.get("notes"))[:8000]
    out["guardrail_notes"] = _coerce_str(raw.get("guardrail_notes"))[:8000]
    paths_raw = raw.get("paths")
    paths: list[str] = []
    if isinstance(paths_raw, list):
        for p in paths_raw:
            if isinstance(p, str):
                s = p.strip()[:2000]
                if s:
                    paths.append(s)
    out["paths"] = paths
    globs_raw = raw.get("allowed_write_globs")
    globs: list[str] = []
    if isinstance(globs_raw, list):
        for g in globs_raw:
            if isinstance(g, str):
                t = g.strip()[:500]
                if t:
                    globs.append(t)
    out["allowed_write_globs"] = globs[:64]
    return out


def normalize_prompt_recipe(raw: Any) -> dict[str, Any]:
    defaults = {
        "recipe_id": "",
        "intent": "clarify",
        "template_ref": "",
        "variables": {},
        "prompt_mode": "static",
        "materialization_inputs": [],
        "placeholder_summary": "",
    }
    if not isinstance(raw, dict):
        return dict(defaults)
    out = {**defaults, **{k: v for k, v in raw.items() if k not in ("variables", "materialization_inputs")}}
    out["recipe_id"] = _coerce_str(raw.get("recipe_id"))[:200]
    out["intent"] = coerce_prompt_intent(raw.get("intent"))
    out["template_ref"] = _coerce_str(raw.get("template_ref"))[:500]
    out["prompt_mode"] = coerce_prompt_mode(raw.get("prompt_mode"))
    out["placeholder_summary"] = _coerce_str(raw.get("placeholder_summary"))[:4000]
    vr = raw.get("variables")
    variables: dict[str, str] = {}
    if isinstance(vr, dict):
        for kk, vv in vr.items():
            key = _coerce_str(kk)[:120]
            if not key:
                continue
            variables[key] = _coerce_str(vv)[:4000]
    out["variables"] = variables
    mi = raw.get("materialization_inputs")
    inputs: list[str] = []
    if isinstance(mi, list):
        for x in mi:
            if isinstance(x, str):
                t = x.strip()[:500]
                if t:
                    inputs.append(t)
    out["materialization_inputs"] = inputs[:64]
    return out


def normalize_prompt_snapshot(raw: Any) -> dict[str, Any] | None:
    if not isinstance(raw, dict):
        return None
    return {
        "snapshot_id": _coerce_str(raw.get("snapshot_id"))[:128] or _new_entry_id(),
        "recipe_id": _coerce_str(raw.get("recipe_id"))[:200],
        "rendered": _coerce_str(raw.get("rendered"))[:200_000],
        "content_hash": _coerce_str(raw.get("content_hash"))[:128],
        "created_at": _coerce_str(raw.get("created_at"))[:64],
    }


def normalize_artifact_status_map(raw: Any) -> dict[str, str]:
    if not isinstance(raw, dict):
        return {}
    out: dict[str, str] = {}
    for k, v in raw.items():
        key = _coerce_str(k)[:200]
        if not key:
            continue
        out[key] = coerce_artifact_status(v)
    return out


def empty_wizard_domain() -> dict[str, Any]:
    return {
        "schema_version": 1,
        "mission_type": "explore",
        "contribution_setup_kind": "single",
        "context_sources": [],
        "foundation_brief": normalize_foundation_brief({}),
        "assumption_ledger": [],
        "artifact_packs": [],
        "target_stage": "idea",
        "autonomy_level": "l0_analyst",
        "mutation_policy": "read_only_analysis",
        "scope_spec": normalize_scope_spec({}),
        "run_plan": normalize_run_plan({}),
        "review_gates": normalize_review_gates([]),
        "artifact_status_by_id": {},
        "recheck_summary": normalize_recheck_summary({}),
        "build_pack_plan": normalize_build_pack_plan({}),
        "prompt_recipe": normalize_prompt_recipe({}),
        "prompt_snapshot": None,
        "artifact_generation": normalize_artifact_generation({}),
    }


def normalize_wizard_domain(raw: Any) -> dict[str, Any]:
    """Merge defaults; coerce enums and nested shapes; preserve unknown top-level keys."""
    defaults = empty_wizard_domain()
    if not isinstance(raw, dict):
        return copy.deepcopy(defaults)

    preserved: dict[str, Any] = {}
    for k, v in raw.items():
        if k not in defaults:
            preserved[k] = copy.deepcopy(v)

    out = dict(defaults)
    out.update({k: v for k, v in raw.items() if k in defaults and k != "schema_version"})
    out["schema_version"] = _coerce_schema_version(raw.get("schema_version"))

    out["mission_type"] = coerce_mission_type(raw.get("mission_type"))
    out["contribution_setup_kind"] = coerce_contribution_setup_kind(raw.get("contribution_setup_kind"))

    cs_raw = raw.get("context_sources")
    sources: list[str] = []
    if isinstance(cs_raw, list):
        for x in cs_raw:
            sources.append(coerce_context_source(x))
    out["context_sources"] = sources

    out["foundation_brief"] = normalize_foundation_brief(raw.get("foundation_brief"))
    out["assumption_ledger"] = normalize_assumption_ledger(raw.get("assumption_ledger"))

    packs_raw = raw.get("artifact_packs")
    packs: list[dict[str, Any]] = []
    if isinstance(packs_raw, list):
        for p in packs_raw:
            packs.append(normalize_artifact_pack(p))
    out["artifact_packs"] = packs

    out["target_stage"] = coerce_target_stage(raw.get("target_stage"))
    out["autonomy_level"] = coerce_autonomy_level(raw.get("autonomy_level"))
    out["mutation_policy"] = coerce_mutation_policy(raw.get("mutation_policy"))

    out["scope_spec"] = normalize_scope_spec(raw.get("scope_spec"))
    out["run_plan"] = normalize_run_plan(raw.get("run_plan"))
    out["review_gates"] = normalize_review_gates(raw.get("review_gates"))
    out["artifact_status_by_id"] = normalize_artifact_status_map(raw.get("artifact_status_by_id"))
    out["recheck_summary"] = normalize_recheck_summary(raw.get("recheck_summary"))
    out["build_pack_plan"] = normalize_build_pack_plan(raw.get("build_pack_plan"))
    out["prompt_recipe"] = normalize_prompt_recipe(raw.get("prompt_recipe"))

    ps = raw.get("prompt_snapshot")
    if ps is None:
        out["prompt_snapshot"] = None
    else:
        out["prompt_snapshot"] = normalize_prompt_snapshot(ps)

    out["artifact_generation"] = normalize_artifact_generation(raw.get("artifact_generation"))

    out.update(preserved)
    out["schema_version"] = _coerce_schema_version(raw.get("schema_version"))
    return out
