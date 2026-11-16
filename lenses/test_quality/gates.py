"""Evaluate quality gates against fixture state."""

from __future__ import annotations

from typing import Any


def _latest_run_for_suite(runs: list[dict[str, Any]], suite_id: str, project: str) -> dict[str, Any] | None:
    cand: list[dict[str, Any]] = []
    for r in runs:
        if not isinstance(r, dict):
            continue
        if str(r.get("suite_id") or "") != suite_id:
            continue
        if project and str(r.get("project") or "").strip() != project:
            continue
        cand.append(r)
    if not cand:
        return None
    cand.sort(key=lambda x: str(x.get("finished_at") or x.get("started_at") or ""), reverse=True)
    return cand[0]


def _open_defects(defects: list[dict[str, Any]], project: str, min_rank: int) -> list[dict[str, Any]]:
    sev_rank = {"critical": 4, "major": 3, "minor": 2, "trivial": 1}
    out: list[dict[str, Any]] = []
    for d in defects:
        if not isinstance(d, dict):
            continue
        if project and str(d.get("project") or "").strip() != project:
            continue
        st = str(d.get("status") or "").lower()
        if st in ("closed", "done", "resolved"):
            continue
        sr = sev_rank.get(str(d.get("severity") or "").lower(), 0)
        if sr >= min_rank:
            out.append(d)
    return out


def evaluate_quality_gates(doc: dict[str, Any], *, project_filter: str | None = None) -> tuple[list[dict[str, Any]], dict[str, Any] | None]:
    """Return (gate_evaluations, release_quality summary)."""
    proj = (project_filter or "").strip()
    runs = [r for r in doc.get("test_runs") or [] if isinstance(r, dict)]
    defects = [d for d in doc.get("defects") or [] if isinstance(d, dict)]
    gates_in = [g for g in doc.get("quality_gates") or [] if isinstance(g, dict)]

    evaluations: list[dict[str, Any]] = []
    blocking_reasons: list[str] = []

    for g in gates_in:
        gid = str(g.get("id") or "")
        name = str(g.get("name") or gid)
        rule = g.get("rule") if isinstance(g.get("rule"), dict) else {}
        rtype = str(rule.get("type") or "").strip()
        passed = True
        detail = ""

        if rtype == "last_suite_run_status":
            sid = str(rule.get("suite_id") or "")
            must = str(rule.get("must_be") or "passed").lower()
            p = str(rule.get("project") or proj or "").strip()
            latest = _latest_run_for_suite(runs, sid, p) if sid else None
            if latest is None:
                passed = False
                detail = f"No test run found for suite {sid!r}"
            else:
                st = str(latest.get("status") or "").lower()
                passed = st == must
                detail = f"Latest run {latest.get('id')!r} status={st!r} (need {must!r})"
        elif rtype == "no_open_defects_min_severity":
            p = str(rule.get("project") or proj or "").strip()
            min_sev = str(rule.get("min_severity") or "major").lower()
            min_rank = {"critical": 4, "major": 3, "minor": 2, "trivial": 1}.get(min_sev, 3)
            openn = _open_defects(defects, p, min_rank)
            passed = len(openn) == 0
            detail = f"{len(openn)} open defect(s) at or above {min_sev}" if not passed else "No blocking open defects"
        elif rtype == "coverage_line_minimum":
            p = str(rule.get("project") or proj or "").strip()
            need = float(rule.get("min_percent") or 0)
            covs = [
                c
                for c in doc.get("coverage_summaries") or []
                if isinstance(c, dict) and (not p or str(c.get("project") or "") == p)
            ]
            best = max((float(c.get("line_percent") or 0) for c in covs), default=0.0)
            passed = best >= need
            detail = f"Line coverage {best:.1f}% (minimum {need:.1f}%)"
        elif rtype == "uat_signoff_required":
            story_ids = rule.get("story_ids")
            want = [str(x) for x in story_ids] if isinstance(story_ids, list) else []
            uats = [u for u in doc.get("uat_signoffs") or [] if isinstance(u, dict)]
            approved = {str(u.get("story_id")) for u in uats if str(u.get("status") or "").lower() in ("approved", "signed_off")}
            missing = [s for s in want if s not in approved]
            passed = len(missing) == 0
            detail = "All listed stories UAT-approved" if passed else f"Missing UAT for: {', '.join(missing)}"
        else:
            passed = True
            detail = "Unknown rule type; not enforced"

        applies_envs = g.get("applies_to_environments")
        envs = [str(x) for x in applies_envs] if isinstance(applies_envs, list) else []
        blocks_release = bool(g.get("blocks_release_train"))

        evaluations.append(
            {
                "gate_id": gid,
                "name": name,
                "passed": passed,
                "detail": detail,
                "applies_to_environments": envs,
                "blocks_release_train": blocks_release,
            }
        )
        if not passed:
            blocking_reasons.append(f"{name}: {detail}")
            if blocks_release:
                pass

    failed_train = [e for e in evaluations if not e["passed"] and e.get("blocks_release_train")]
    any_failed = [e for e in evaluations if not e["passed"]]
    release_quality = (
        {
            "ready": len(failed_train) == 0,
            "failed_gates": [e["gate_id"] for e in any_failed],
            "blocking_train_gates": [e["gate_id"] for e in failed_train],
            "summary": "; ".join(blocking_reasons) if blocking_reasons else "All gates passed",
        }
        if evaluations
        else None
    )

    return evaluations, release_quality


def quality_gate_promotion_blockers(
    evaluations: list[dict[str, Any]],
    promotions: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Synthetic blocked_promotions rows for failed gates that apply to target env."""
    out: list[dict[str, Any]] = []
    seen: set[str] = set()
    for prom in promotions:
        if not isinstance(prom, dict):
            continue
        pid = str(prom.get("id") or "")
        to_env = str(prom.get("to_env") or "")
        if not pid or not to_env:
            continue
        for ev in evaluations:
            if ev.get("passed"):
                continue
            envs = ev.get("applies_to_environments") or []
            if not isinstance(envs, list) or to_env not in envs:
                continue
            key = f"{pid}:{ev.get('gate_id')}"
            if key in seen:
                continue
            seen.add(key)
            out.append(
                {
                    "promotion_id": pid,
                    "reason": f"quality_gate_failed:{ev.get('gate_id')}",
                    "detail": f"{ev.get('name')}: {ev.get('detail')}",
                }
            )
    return out


def build_run_comparisons(runs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Pair runs that declare compared_to_run_id for historical diff."""
    by_id = {str(r.get("id")): r for r in runs if isinstance(r, dict) and r.get("id")}
    out: list[dict[str, Any]] = []
    for r in runs:
        if not isinstance(r, dict):
            continue
        prev_id = str(r.get("compared_to_run_id") or "").strip()
        if not prev_id or prev_id not in by_id:
            continue
        prev = by_id[prev_id]
        out.append(
            {
                "current_run_id": str(r.get("id")),
                "previous_run_id": prev_id,
                "suite_id": str(r.get("suite_id") or ""),
                "delta_passed": int(r.get("passed") or 0) - int(prev.get("passed") or 0),
                "delta_failed": int(r.get("failed") or 0) - int(prev.get("failed") or 0),
                "delta_skipped": int(r.get("skipped") or 0) - int(prev.get("skipped") or 0),
            }
        )
    return out
