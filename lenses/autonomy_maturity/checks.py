"""Deterministic per-repo signals for the autonomy maturity assessment.

Signals follow Blueprints ``AUTONOMY-MATURITY-FRAMEWORK.md``: gate definition
(forge config + rules + CI + tests), demonstrated run evidence (assay records
with a declared level/sub-level), repeatability, and operational metrics.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

# Levels ordered for "highest observed" comparisons.
LEVEL_ORDER: dict[str, int] = {f"L{i}": i for i in range(0, 9)}

REPEATABLE_MIN_RUNS = 5
REPEATABLE_MAX_ESCALATION_RATE = 0.4
_MAX_ASSAY_FILES = 200


@dataclass
class RunEvidence:
    level: str
    sublevel: str | None
    ok: bool
    escalated: bool | None = None


@dataclass
class Signals:
    forge_config_present: bool = False
    forge_config_assay_keys: bool = False
    cursor_rules_present: bool = False
    ci_present: bool = False
    tests_present: bool = False
    runs: list[RunEvidence] = field(default_factory=list)


def _has_ci(repo: Path) -> bool:
    if (repo / ".github" / "workflows").is_dir():
        return any((repo / ".github" / "workflows").glob("*.y*ml"))
    return any((repo / n).exists() for n in (".gitlab-ci.yml", "Jenkinsfile", ".circleci"))


def _has_tests(repo: Path) -> bool:
    if (repo / "tests").is_dir():
        return True
    try:
        return any(repo.glob("test_*.py")) or any(repo.glob("*/test_*.py"))
    except OSError:
        return False


def _forge_config_signals(repo: Path) -> tuple[bool, bool]:
    cfg = repo / "forge" / "forge.config.yaml"
    if not cfg.is_file():
        return False, False
    try:
        text = cfg.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return True, False
    keys = ("tests_pass", "acceptance_criteria_met", "risks_reviewed")
    return True, all(k in text for k in keys)


def _load_run_evidence(repo: Path) -> list[RunEvidence]:
    """Best-effort scan of Dark Factory style machine records: runs/**/machine/assay.json."""
    runs_dir = repo / "runs"
    if not runs_dir.is_dir():
        return []
    out: list[RunEvidence] = []
    try:
        assay_files = sorted(runs_dir.glob("**/machine/assay.json"))[:_MAX_ASSAY_FILES]
    except OSError:
        return []
    for f in assay_files:
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        if not isinstance(data, dict):
            continue
        level = str(data.get("level") or "").upper()
        if level not in LEVEL_ORDER:
            continue
        sublevel = data.get("sublevel")
        escalated: bool | None = None
        run_json = f.parent / "run.json"
        if run_json.is_file():
            try:
                run_data = json.loads(run_json.read_text(encoding="utf-8"))
                if isinstance(run_data, dict) and "escalated" in run_data:
                    escalated = bool(run_data["escalated"])
            except (OSError, ValueError):
                pass
        out.append(
            RunEvidence(
                level=level,
                sublevel=str(sublevel).upper() if sublevel else None,
                ok=bool(data.get("ok")),
                escalated=escalated,
            )
        )
    return out


def collect_signals(repo_path: Path) -> Signals:
    repo = repo_path.resolve()
    cfg_present, cfg_keys = _forge_config_signals(repo)
    rules_dir = repo / ".cursor" / "rules"
    rules_present = rules_dir.is_dir() and any(rules_dir.iterdir())
    return Signals(
        forge_config_present=cfg_present,
        forge_config_assay_keys=cfg_keys,
        cursor_rules_present=rules_present,
        ci_present=_has_ci(repo),
        tests_present=_has_tests(repo),
        runs=_load_run_evidence(repo),
    )


def green_runs_by_level(runs: list[RunEvidence]) -> dict[str, list[RunEvidence]]:
    grouped: dict[str, list[RunEvidence]] = {}
    for r in runs:
        if r.ok:
            grouped.setdefault(r.level, []).append(r)
    return grouped


def escalation_rate(runs: list[RunEvidence]) -> float | None:
    """Loop-escalation rate over runs that recorded the flag; None when unknown."""
    known = [r for r in runs if r.escalated is not None]
    if not known:
        return None
    return sum(1 for r in known if r.escalated) / len(known)
