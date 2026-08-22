"""Classify Copilot turns into retrieval strategies (single-shot vs map-reduce)."""

from __future__ import annotations

import os
import re
from typing import Any, Literal

CopilotStrategy = Literal["single_shot", "portfolio_map_reduce", "search_map_reduce"]

PORTFOLIO_GIT_THRESHOLD = 12

_EACH_ALL_RE = re.compile(
    r"\b(each|every|all|everyone)\b.*\b(project|repo|repository|repositories|folder|folders|workspace|portfolio)\b"
    r"|\b(project|repo|repository|repositories)\b.*\b(each|every|all)\b",
    re.IGNORECASE,
)
_BROAD_SEARCH_RE = re.compile(
    r"\b(across|throughout|everywhere|whole workspace|entire workspace|all repos?|all projects?)\b",
    re.IGNORECASE,
)
_ENUMERATE_RE = re.compile(
    r"\b(list|describe|summarize|summary of|overview of)\b.*\b(project|repo|repository|portfolio|workspace)\b",
    re.IGNORECASE,
)


def _git_child_count(scan_state: dict[str, Any]) -> int:
    children = scan_state.get("children") if isinstance(scan_state, dict) else None
    if not isinstance(children, list):
        return 0
    return sum(1 for ch in children if isinstance(ch, dict) and ch.get("is_git"))


def _total_child_count(scan_state: dict[str, Any]) -> int:
    children = scan_state.get("children") if isinstance(scan_state, dict) else None
    if not isinstance(children, list):
        return 0
    return sum(1 for ch in children if isinstance(ch, dict) and str(ch.get("name") or "").strip())


def classify_copilot_strategy(
    user_message: str,
    *,
    studio_route: str,
    scan_state: dict[str, Any],
) -> CopilotStrategy:
    """Heuristic strategy router (no extra LLM call)."""
    msg = (user_message or "").strip()
    route = (studio_route or "").strip().lower()
    git_n = _git_child_count(scan_state)
    total_n = _total_child_count(scan_state)

    if route == "projects" and msg:
        if _EACH_ALL_RE.search(msg) or _ENUMERATE_RE.search(msg):
            return "portfolio_map_reduce"
        if git_n >= PORTFOLIO_GIT_THRESHOLD and re.search(
            r"\b(one sentence|one line|brief|short)\b", msg, re.I
        ):
            return "portfolio_map_reduce"

    if msg and (_EACH_ALL_RE.search(msg) or _ENUMERATE_RE.search(msg)) and git_n >= 8:
        return "portfolio_map_reduce"

    if msg and _BROAD_SEARCH_RE.search(msg) and total_n >= 8:
        return "search_map_reduce"

    return "single_shot"


def map_reduce_enabled(strategy: CopilotStrategy, git_count: int) -> bool:
    """Feature gate for map-reduce orchestration."""
    if strategy == "single_shot":
        return False
    raw = (os.environ.get("LENSES_COPILOT_MAP_REDUCE") or "").strip().lower()
    if raw in ("0", "false", "no", "off"):
        return False
    if raw in ("1", "true", "yes", "on"):
        return True
    if strategy == "portfolio_map_reduce" and git_count > 8:
        return True
    if strategy == "search_map_reduce" and git_count > 8:
        return True
    return False
