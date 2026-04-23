"""Resolve Git branch naming for Docs Health from repo layout + Forge blueprints conventions.

Discovery order (see ``docs/docs-health-git-branch-policy.md``):

1. ``<project>/forge/branching.yml`` — optional ``docs_health_branch_style`` / ``trunk``.
2. ``<project>/docs/process/branching-profile.md`` — lane keywords (heuristic).
3. Embedded ``<project>/blueprints/.../BRANCHING-STRATEGY.md`` (submodule copy in consumer).
4. ``<workspace_root>/blueprints/.../BRANCHING-STRATEGY.md`` when present (workspace-level clone).
5. Fallback: Forge Team tier — trunk ``main``, topic branches ``feature/*`` / ``fix/*`` (see forge-lenses ``docs/GIT-WORKFLOW.md``).
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

BranchStyle = Literal["feature_prefixed", "legacy_docs_health"]

_BLUEPRINTS_BRANCHING = Path("blueprints") / "sdlc" / "methodologies" / "forge" / "setup" / "BRANCHING-STRATEGY.md"
_FORGE_BRANCHING_YML = Path("forge") / "branching.yml"
_DOCS_PROCESS_PROFILE = Path("docs") / "process" / "branching-profile.md"


@dataclass(frozen=True)
class GitBranchPolicy:
    """Resolved policy for naming remediation branches."""

    trunk: str
    style: BranchStyle
    source: str

    def format_docs_health_branch(self, session_id_hex: str) -> str:
        sid = (session_id_hex or "").strip()
        short = sid[:10] if len(sid) >= 10 else sid or "session"
        if self.style == "legacy_docs_health":
            return f"docs-health/{short}"
        return f"feature/docs-health-{short}"


def _read_branching_yml(project_root: Path) -> dict[str, Any] | None:
    p = project_root / _FORGE_BRANCHING_YML
    if not p.is_file():
        return None
    try:
        from yaml import safe_load  # noqa: PLC0415

        raw = p.read_text(encoding="utf-8")
        data = safe_load(raw)
    except Exception:
        return None
    return data if isinstance(data, dict) else None


def _profile_mentions_lanes(profile_text: str) -> bool:
    t = profile_text.lower()
    return any(x in t for x in ("product/", "iter/", "spark/", "forge-native", "lane model"))


def _resolve_from_branching_yml(data: dict[str, Any]) -> tuple[str | None, BranchStyle | None, str | None]:
    trunk = str(data.get("trunk") or data.get("default_branch") or "").strip() or None
    style_raw = str(data.get("docs_health_branch_style") or data.get("docs_health_branches") or "").strip().lower()
    if style_raw in ("legacy", "docs-health", "docs_health"):
        return trunk or "main", "legacy_docs_health", "forge/branching.yml"
    if style_raw in ("feature", "team", "github_flow", "feature_prefixed"):
        return trunk or "main", "feature_prefixed", "forge/branching.yml"
    lanes = bool(data.get("lanes")) or bool(data.get("use_forge_lanes"))
    if lanes:
        return trunk or "main", "feature_prefixed", "forge/branching.yml(lanes)"
    return trunk, None, None


def _blueprints_strategy_exists(root: Path) -> bool:
    return (root / _BLUEPRINTS_BRANCHING).is_file()


def resolve_git_branch_policy(project_root: Path, workspace_root: Path | None = None) -> GitBranchPolicy:
    """
    :param project_root: Git checkout root for the project (workspace child).
    :param workspace_root: Optional Lenses workspace root for sibling ``blueprints/``.
    """
    pr = project_root.resolve()

    yml = _read_branching_yml(pr)
    if yml:
        trunk, st, src = _resolve_from_branching_yml(yml)
        if st is not None:
            return GitBranchPolicy(trunk=trunk or "main", style=st, source=src or "forge/branching.yml")
        if trunk:
            return GitBranchPolicy(trunk=trunk, style="feature_prefixed", source=src or "forge/branching.yml(trunk_only)")

    profile = pr / _DOCS_PROCESS_PROFILE
    if profile.is_file():
        try:
            text = profile.read_text(encoding="utf-8", errors="replace")
        except OSError:
            text = ""
        if _profile_mentions_lanes(text):
            return GitBranchPolicy(trunk="main", style="feature_prefixed", source="docs/process/branching-profile.md")

    if _blueprints_strategy_exists(pr):
        return GitBranchPolicy(trunk="main", style="feature_prefixed", source="blueprints/…/BRANCHING-STRATEGY.md")

    if workspace_root is not None:
        wr = workspace_root.resolve()
        if _blueprints_strategy_exists(wr):
            return GitBranchPolicy(trunk="main", style="feature_prefixed", source="workspace/blueprints/…")

    return GitBranchPolicy(trunk="main", style="feature_prefixed", source="fallback_team_tier")
