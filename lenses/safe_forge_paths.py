"""Allowlisted workspace-relative paths for Forge daily artifacts (read-only serving)."""

from __future__ import annotations

from pathlib import Path
from urllib.parse import urlencode


def safe_forge_workspace_file(workspace_root: Path, rel: str) -> Path | None:
    """
    Resolve ``rel`` under ``workspace_root`` if it matches an allowlisted Forge artifact path.

    Allowed (markdown only):

    - ``…/forge/charge.md``
    - ``…/forge/journal/*.md``
    - ``…/ember-logs/*.md``
    - ``…/forge-logs/**/*.md`` (any depth under ``forge-logs``)
    """
    if not rel or ".." in rel.split("/") or rel.startswith(("/", "\\")):
        return None
    rel_norm = rel.replace("\\", "/").strip("/")
    candidate = (workspace_root / rel_norm).resolve()
    wr = workspace_root.resolve()
    try:
        candidate.relative_to(wr)
    except ValueError:
        return None
    if not candidate.is_file():
        return None
    if candidate.suffix.lower() != ".md":
        return None
    parts = rel_norm.split("/")
    if not parts:
        return None
    if parts[-2:] == ["forge", "charge.md"]:
        return candidate
    if (
        len(parts) >= 3
        and parts[-3] == "forge"
        and parts[-2] == "journal"
    ):
        return candidate
    if len(parts) >= 2 and parts[-2] == "ember-logs":
        return candidate
    if "forge-logs" in parts:
        return candidate
    return None


def workspace_md_view_link(rel_path: str) -> str:
    return f"/workspace-md/view?{urlencode({'p': rel_path})}"
