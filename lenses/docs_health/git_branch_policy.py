"""Resolve Docs Health branch naming from Branch Steward policy resolution."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from lenses.branch_steward_policy import resolve_branch_steward_policy

BranchStyle = Literal["feature_prefixed", "legacy_docs_health"]


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


def resolve_git_branch_policy(project_root: Path, workspace_root: Path | None = None) -> GitBranchPolicy:
    policy = resolve_branch_steward_policy(project_root.resolve(), workspace_root=workspace_root)
    return GitBranchPolicy(trunk=policy.trunk, style=policy.docs_health_style, source=policy.source)
