"""Allowlisted workspace-relative paths for Forge daily artifacts (read-only serving)."""

from __future__ import annotations

from pathlib import Path
from urllib.parse import urlencode


def workspace_md_path_pattern_category(rel_norm: str) -> str | None:
    """
    Return a coarse category if ``rel_norm`` matches allowlisted patterns (slashes, no leading slash).

    Categories: ``charge``, ``journal``, ``ember``, ``forge_logs``.
    """
    if not rel_norm or ".." in rel_norm.split("/"):
        return None
    rel_clean = rel_norm.replace("\\", "/").strip("/")
    parts = rel_clean.split("/")
    if not parts:
        return None
    if parts[-2:] == ["forge", "charge.md"]:
        return "charge"
    if len(parts) >= 3 and parts[-3] == "forge" and parts[-2] == "journal":
        return "journal"
    if len(parts) >= 2 and parts[-2] == "ember-logs":
        return "ember"
    if "forge-logs" in parts:
        return "forge_logs"
    return None


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
    if workspace_md_path_pattern_category(rel_norm) is None:
        return None
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
    return candidate


def iter_workspace_md_index(
    workspace_root: Path,
    *,
    max_files: int = 500,
) -> tuple[list[dict[str, str]], bool]:
    """
    Discover allowlisted markdown files under the workspace (root and immediate child directories).

    Returns (files, truncated) where each file is ``{"rel_path", "category"}`` sorted by path.
    """
    wr = workspace_root.resolve()
    found: dict[str, str] = {}

    def add_rel(rel_posix: str) -> None:
        if len(found) >= max_files:
            return
        sp = safe_forge_workspace_file(wr, rel_posix)
        if sp is None:
            return
        cat = workspace_md_path_pattern_category(rel_posix)
        if cat:
            found[rel_posix] = cat

    bases: list[Path] = [wr]
    try:
        for c in sorted(wr.iterdir(), key=lambda x: x.name.lower()):
            if c.is_dir() and not c.name.startswith("."):
                bases.append(c)
    except OSError:
        pass

    for base in bases:
        if len(found) >= max_files:
            break

        charge = base / "forge" / "charge.md"
        if charge.is_file():
            add_rel(charge.relative_to(wr).as_posix())

        jdir = base / "forge" / "journal"
        if jdir.is_dir():
            for p in sorted(jdir.glob("*.md")):
                if len(found) >= max_files:
                    break
                add_rel(p.relative_to(wr).as_posix())

        ember = base / "ember-logs"
        if ember.is_dir():
            for p in sorted(ember.glob("*.md")):
                if len(found) >= max_files:
                    break
                add_rel(p.relative_to(wr).as_posix())

        froot = base / "forge-logs"
        if froot.is_dir():
            for p in sorted(froot.rglob("*.md")):
                if len(found) >= max_files:
                    break
                add_rel(p.relative_to(wr).as_posix())

    items = [{"rel_path": k, "category": v} for k, v in sorted(found.items(), key=lambda x: x[0].lower())]
    truncated = len(found) >= max_files
    return items, truncated


def workspace_md_view_link(rel_path: str) -> str:
    return f"/workspace-md/view?{urlencode({'p': rel_path})}"


def roadmap_timeline_view_link(rel_path: str) -> str:
    """Classic HTML view for a workspace ROADMAP.md (same rules as ``/roadmaps/timeline``)."""
    return f"/roadmaps/timeline?{urlencode({'p': rel_path})}"
