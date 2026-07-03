"""Deterministic plan builder for Foundry (no LLM required for MVP)."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from lenses.foundry.target_resolve import allowed_files_for_body, resolve_foundry_target


def _default_allowed_files(target: Path, goal: str) -> list[str]:
    g = goal.lower()
    if "multiply" in g or "engine" in g:
        return ["src/dfcalc/engine.py"]
    if (target / "src" / "dfcalc" / "engine.py").is_file():
        return ["src/dfcalc/engine.py"]
    if (target / "calculator.py").is_file():
        return ["calculator.py"]
    return []


def _verification_for_target(target: Path, goal: str) -> list[str]:
    g = goal.lower()
    if "multiply" in g and (target / "tests" / "test_engine.py").is_file():
        return ["python3", "-m", "pytest", "-q", "tests/test_engine.py::test_multiply"]
    if (target / "tests").is_dir():
        return ["python3", "-m", "pytest", "-q"]
    return ["python3", "-m", "pytest", "-q"]


def build_plan(body: dict[str, Any], workspace_root: Path) -> dict[str, Any]:
    goal = str(body.get("goal") or "").strip()
    if not goal:
        return {"ok": False, "error": "goal_required"}
    level = str(body.get("level") or "L1").strip().upper()
    if level not in ("L1", "L2", "L3"):
        return {"ok": False, "error": "invalid_level", "detail": "Only L1 is available; L2/L3 are stubs"}
    if level != "L1":
        return {"ok": False, "error": "not_implemented", "reason": "dark_factory_level_not_wired"}

    target_raw = str(body.get("target") or body.get("target_path") or "").strip()
    project = str(body.get("project") or "").strip()
    target, file_hint = resolve_foundry_target(workspace_root, body)
    if target is None or not target.is_dir():
        guess = target_raw or project or str(workspace_root)
        p = Path(guess)
        if not p.is_absolute():
            p = (workspace_root / guess).resolve()
        return {"ok": False, "error": "target_not_found", "target": str(p)}

    allowed_files = allowed_files_for_body(
        body,
        repo_dir=target,
        goal=goal,
        file_hint=file_hint,
        default_fn=_default_allowed_files,
    )

    patch_id = re.sub(r"[^a-zA-Z0-9]+", "-", goal.lower())[:40].strip("-") or "unit-1"
    unit = {
        "patch_id": patch_id,
        "goal": goal,
        "allowed_files": allowed_files,
        "forbidden_files": ["tests/**", "test_*.py"],
        "acceptance_criteria": ["pytest passes for the stated goal"],
        "verification_commands": _verification_for_target(target, goal),
    }
    return {
        "ok": True,
        "level": level,
        "execution_mode": str(body.get("execution_mode") or "draft"),
        "project": project,
        "target": str(target),
        "goal": goal,
        "units": [unit],
    }
