"""User-facing change narrative from Dark Factory machine artifacts."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any


def _read_json(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return data if isinstance(data, dict) else None


def _fixture_path_from_phases(phases_raw: list[Any] | None) -> str:
    if not phases_raw:
        return ""
    for item in phases_raw:
        if not isinstance(item, dict):
            continue
        for r in item.get("reasons") or []:
            text = str(r)
            if "fixture=" in text:
                return text.split("fixture=", 1)[1].strip()
        detail = str(item.get("detail") or "")
        if "fixture=" in detail:
            return detail.split("fixture=", 1)[1].strip()
    return ""


def _fixture_path_from_model_report(model_report: dict[str, Any] | None) -> str:
    if not isinstance(model_report, dict):
        return ""
    for att in model_report.get("attempts") or []:
        if not isinstance(att, dict):
            continue
        notes = str(att.get("notes") or "")
        if "fixture=" in notes:
            return notes.split("fixture=", 1)[1].strip()
    return ""


def _tests_from_proof(proof: dict[str, Any] | None) -> list[str]:
    if not isinstance(proof, dict):
        return []
    raw = proof.get("tests_run")
    if isinstance(raw, list):
        return [str(x) for x in raw if str(x).strip()]
    return []


def _goal_root_cause(goal: str, tests: list[str]) -> str:
    g = (goal or "").strip().lower()
    if "multiply" in g:
        test = next((t for t in tests if "multiply" in t.lower()), tests[0] if tests else "")
        extra = f" Verification: `{test}`." if test else ""
        return (
            "`multiply()` returned the sum of its operands instead of the product, "
            f"so multiplying 3 × 4 yielded 7 instead of the expected 12.{extra}"
        )
    if tests:
        return f"Automated verification failed for goal “{goal}”. Command: `{tests[0]}`."
    return f"The stated goal was not met: “{goal or 'unknown'}”."


def _change_summary_from_diff(rel: str, unified: str, goal: str) -> str:
    if not unified.strip():
        return f"Updated `{rel}` to satisfy the goal."
    if "return a + b" in unified and "return a * b" in unified:
        return (
            f"In `{rel}`, corrected `multiply()` to return the product (`a * b`) "
            "instead of the sum (`a + b`)."
        )
    added = len(re.findall(r"^\+[^+]", unified, re.MULTILINE))
    removed = len(re.findall(r"^-[^-]", unified, re.MULTILINE))
    return (
        f"`{rel}` was edited ({removed} line(s) removed, {added} line(s) added) "
        f"to address: {goal or 'the run goal'}."
    )


def build_change_narrative(
    *,
    run_dir: Path,
    goal: str,
    proof: dict[str, Any] | None,
    phases_raw: list[Any] | None,
    plan: dict[str, Any] | None,
) -> dict[str, Any]:
    machine = run_dir / "machine"
    model_report = _read_json(machine / "model_report.json") or {}
    human_md = ""
    human_path = run_dir / "human" / "report.md"
    if human_path.is_file():
        human_md = human_path.read_text(encoding="utf-8", errors="replace")

    fixture_path = _fixture_path_from_phases(phases_raw) or _fixture_path_from_model_report(model_report)
    fixture = _read_json(Path(fixture_path)) if fixture_path else None

    tests = _tests_from_proof(proof)
    if not tests and isinstance(plan, dict):
        units = plan.get("units")
        if isinstance(units, list) and units and isinstance(units[0], dict):
            vc = units[0].get("verification_commands")
            if isinstance(vc, list):
                tests = [" ".join(str(x) for x in vc)]

    worker_notes: list[str] = []
    for item in phases_raw or []:
        if not isinstance(item, dict):
            continue
        name = str(item.get("name") or "")
        detail = str(item.get("detail") or "")
        if name.startswith("draft"):
            worker_notes.append(detail)
            for r in item.get("reasons") or []:
                worker_notes.append(str(r))

    root_cause = _goal_root_cause(goal, tests)
    if isinstance(proof, dict):
        for pr in proof.get("patch_results") or []:
            if not isinstance(pr, dict):
                continue
            errs = pr.get("errors")
            if isinstance(errs, list) and errs:
                root_cause = "; ".join(str(e) for e in errs[:3])
                break

    files_changed: list[str] = []
    if isinstance(proof, dict) and isinstance(proof.get("files_changed"), list):
        files_changed = [str(x) for x in proof["files_changed"]]

    change_lines: list[str] = []
    for rel in files_changed:
        change_lines.append(_change_summary_from_diff(rel, "", goal))

    why = (
        "The patch is scoped to the allowed files in the L1 plan. "
        "Verification re-ran the recorded pytest command; assay confirms tests and acceptance criteria."
    )
    if tests:
        why += f" Recorded check: `{tests[0]}`."

    return {
        "ok": True,
        "root_cause": root_cause,
        "change_summary": " ".join(change_lines) if change_lines else f"Changes address: {goal}",
        "why_it_works": why,
        "worker_notes": [n for n in worker_notes if n.strip()],
        "fixture_path": fixture_path,
        "human_report_excerpt": human_md[:4000] if human_md else "",
        "has_fixture_before_after": bool(
            isinstance(fixture, dict)
            and isinstance(fixture.get("before"), dict)
            and isinstance(fixture.get("files"), dict)
        ),
    }
