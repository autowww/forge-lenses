"""Deterministic chat intake → plan request fields."""

from __future__ import annotations

import re
from typing import Any


def parse_intake_message(message: str, *, default_project: str = "") -> dict[str, Any]:
    text = (message or "").strip()
    lower = text.lower()
    goal = text
    level = "L1"
    target = ""

    if "multiply" in lower or "fix failing" in lower:
        goal = "fix failing multiply"
        target = "src/dfcalc/engine.py"

    m_level = re.search(r"\bL([123])\b", text, re.I)
    if m_level:
        level = f"L{m_level.group(1)}"

    m_target = re.search(r"#([\w./-]+)", text)
    if m_target:
        target = m_target.group(1)

    m_project = re.search(r"@([\w.-]+)", text)
    project = m_project.group(1) if m_project else default_project

    return {
        "ok": True,
        "goal": goal,
        "level": level,
        "target": target,
        "project": project,
        "source": "fallback_parser",
    }
