"""Aggregate autonomy maturity signals into observed level/grade, score, and recommendations.

Score model (Blueprints AUTONOMY-MATURITY-FRAMEWORK.md):
``score = 40*gate_definition + 30*demonstrated_evidence + 20*repeatability + 10*operational_metrics``
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from lenses.autonomy_maturity.checks import (
    LEVEL_ORDER,
    REPEATABLE_MAX_ESCALATION_RATE,
    REPEATABLE_MIN_RUNS,
    Signals,
    collect_signals,
    escalation_rate,
    green_runs_by_level,
)

SCORE_WEIGHTS: dict[str, int] = {
    "gate_definition": 40,
    "demonstrated_evidence": 30,
    "repeatability": 20,
    "operational_metrics": 10,
}


def _gate_definition(sig: Signals, recs: list[str]) -> float:
    parts = []
    if sig.forge_config_present and sig.forge_config_assay_keys:
        parts.append(1.0)
    elif sig.forge_config_present:
        parts.append(0.5)
        recs.append(
            "forge/forge.config.yaml exists but is missing assay keys — add "
            "tests_pass, acceptance_criteria_met, and risks_reviewed to unlock gate scoring."
        )
    else:
        parts.append(0.0)
        recs.append(
            "Add forge/forge.config.yaml with the three core assay keys "
            "(tests_pass, acceptance_criteria_met, risks_reviewed) to unlock gate scoring."
        )
    if sig.cursor_rules_present:
        parts.append(1.0)
    else:
        parts.append(0.0)
        recs.append("Sync Forge Cursor rules into .cursor/rules to define agent guardrails.")
    if sig.ci_present:
        parts.append(1.0)
    else:
        parts.append(0.0)
        recs.append("Add a CI entrypoint (e.g. .github/workflows/ci.yml) so runs have a green definition.")
    if sig.tests_present:
        parts.append(1.0)
    else:
        parts.append(0.0)
        recs.append("Add a test suite — without tests no autonomy level can produce tests_pass evidence.")
    return sum(parts) / len(parts)


def _observed(sig: Signals, recs: list[str]) -> tuple[str, str, str | None, dict[str, Any]]:
    """Return (level, grade, best_sublevel, evidence_summary)."""
    grouped = green_runs_by_level(sig.runs)
    if not grouped:
        recs.append(
            "No unattended runs recorded — run one L1.1 campaign item against a "
            "provided failing test to earn L1.1b."
        )
        return "L0", "a", None, {"green_runs": 0, "levels": {}}
    best = max(grouped, key=lambda lv: LEVEL_ORDER[lv])
    best_runs = grouped[best]
    sublevels = [r.sublevel for r in best_runs if r.sublevel]
    best_sublevel = sublevels[-1] if sublevels else None
    rate = escalation_rate(best_runs)
    grade = "b"
    if len(best_runs) >= REPEATABLE_MIN_RUNS and rate is not None and rate < REPEATABLE_MAX_ESCALATION_RATE:
        grade = "c"
    else:
        missing = max(0, REPEATABLE_MIN_RUNS - len(best_runs))
        claim = best_sublevel or best
        if missing:
            recs.append(
                f"{claim} demonstrated; {missing} more green run(s) at "
                f"< {int(REPEATABLE_MAX_ESCALATION_RATE * 100)}% escalation promote it to {claim}c."
            )
        elif rate is None:
            recs.append(
                f"{claim} has {len(best_runs)} green runs but no escalation flags recorded — "
                "record escalated true/false per run to qualify for grade c."
            )
        else:
            recs.append(
                f"{claim} escalation rate {rate:.0%} is above the "
                f"{int(REPEATABLE_MAX_ESCALATION_RATE * 100)}% bar — decompose further or lower the declared level."
            )
    summary = {
        "green_runs": sum(len(v) for v in grouped.values()),
        "levels": {lv: len(v) for lv, v in grouped.items()},
        "escalation_rate": rate,
    }
    return best, grade, best_sublevel, summary


def build_project_payload(repo_path: Path, project_name: str) -> dict[str, Any]:
    """Full assessment for one repo: observed claim, component scores, recommendations."""
    recs: list[str] = []
    sig = collect_signals(repo_path)

    gate = _gate_definition(sig, recs)
    level, grade, best_sublevel, evidence = _observed(sig, recs)
    demonstrated = 1.0 if evidence["green_runs"] > 0 else 0.0
    best_level_runs = evidence["levels"].get(level, 0) if level != "L0" else 0
    repeatability = min(1.0, best_level_runs / REPEATABLE_MIN_RUNS)
    rate = evidence.get("escalation_rate")
    operational = 0.5 if (grade == "c" and rate is not None) else 0.0
    if grade == "c":
        recs.append(
            "Grade c reached — sustain a falling escalation trend over 30 days with "
            "review sampling to qualify for grade d."
        )

    components = {
        "gate_definition": gate,
        "demonstrated_evidence": demonstrated,
        "repeatability": repeatability,
        "operational_metrics": operational,
    }
    score = int(round(sum(SCORE_WEIGHTS[k] * v for k, v in components.items())))
    claim_core = best_sublevel or level
    claim = f"{claim_core}{grade}" if level != "L0" else "L0a"

    return {
        "ok": True,
        "project": project_name,
        "observed_level": level,
        "observed_sublevel": best_sublevel,
        "observed_grade": grade,
        "claim": f"{claim} in {project_name}",
        "score": score,
        "components": components,
        "weights": SCORE_WEIGHTS,
        "signals": {
            "forge_config_present": sig.forge_config_present,
            "forge_config_assay_keys": sig.forge_config_assay_keys,
            "cursor_rules_present": sig.cursor_rules_present,
            "ci_present": sig.ci_present,
            "tests_present": sig.tests_present,
        },
        "run_evidence": evidence,
        "recommendations": recs,
        "note": (
            "Observed from repo signals per Blueprints AUTONOMY-MATURITY-FRAMEWORK.md; "
            "Wizard planning intent is never counted as evidence."
        ),
    }


def build_overview_payload(workspace_root: Path, scan_state: dict[str, Any]) -> dict[str, Any]:
    """Workspace overview: one row per git child, weakest score first."""
    rows: list[dict[str, Any]] = []
    for ch in scan_state.get("children") or []:
        if not isinstance(ch, dict) or not ch.get("is_git"):
            continue
        name = str(ch.get("name", "")).strip()
        path_s = str(ch.get("path", "")).strip()
        if not name or not path_s:
            continue
        try:
            report = build_project_payload(Path(path_s), name)
        except OSError:
            continue
        rows.append(
            {
                "project": name,
                "score": report["score"],
                "observed_level": report["observed_level"],
                "observed_sublevel": report["observed_sublevel"],
                "observed_grade": report["observed_grade"],
                "claim": report["claim"],
                "recommendations": report["recommendations"][:3],
            }
        )
    rows.sort(key=lambda r: (r["score"], r["project"]))
    return {
        "ok": True,
        "projects": rows,
        "count": len(rows),
        "note": "Scores follow the Blueprints autonomy maturity framework; weakest first.",
    }
