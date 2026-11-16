"""Resolve Foundry ``project`` + file hint into a repo directory."""

from __future__ import annotations

from pathlib import Path
from typing import Any


def _norm_rel(path: str) -> str:
    return path.replace("\\", "/").lstrip("/")


def resolve_foundry_target(
    workspace_root: Path,
    body: dict[str, Any],
) -> tuple[Path | None, str]:
    """Return ``(repo_dir, optional_file_hint_under_repo)``.

    Studio sends ``@project`` plus ``#target`` as a *file* path (e.g. ``src/dfcalc/engine.py``).
    Older clients sent ``target`` as the repo root — both shapes are accepted.
    """
    project = str(body.get("project") or "").strip()
    raw = str(body.get("target_path") or body.get("target") or "").strip()

    if project:
        proj = Path(project)
        if not proj.is_absolute():
            proj = (workspace_root / project).resolve()
        else:
            proj = proj.resolve()
        if proj.is_dir():
            file_hint = ""
            if raw:
                rel = _norm_rel(raw)
                if (proj / rel).is_file():
                    file_hint = rel
                elif "/" in rel or rel.endswith(".py"):
                    file_hint = rel
            return proj, file_hint

    if not raw:
        return None, ""

    p = Path(raw)
    resolved = p.resolve() if p.is_absolute() else (workspace_root / raw).resolve()
    if resolved.is_dir():
        return resolved, ""
    if resolved.is_file():
        try:
            rel = str(resolved.relative_to(workspace_root)).replace("\\", "/")
        except ValueError:
            rel = resolved.name
        parts = rel.split("/", 1)
        if len(parts) == 2:
            proj = (workspace_root / parts[0]).resolve()
            if proj.is_dir():
                return proj, parts[1]
        return resolved.parent, resolved.name

    return None, ""


def allowed_files_for_body(
    body: dict[str, Any],
    *,
    repo_dir: Path,
    goal: str,
    file_hint: str,
    default_fn,
) -> list[str]:
    allowed = body.get("allowed_files")
    if isinstance(allowed, list) and allowed:
        return [str(x) for x in allowed]
    if file_hint:
        return [file_hint]
    return default_fn(repo_dir, goal)
