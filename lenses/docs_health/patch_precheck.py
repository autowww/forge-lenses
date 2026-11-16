"""Deterministic checks for proposed docs patches (before apply / alongside LLM review)."""

from __future__ import annotations

from pathlib import Path
from typing import Any


def precheck_docs_patch(
    child: Path,
    *,
    project_slug: str,
    patch: dict[str, str],
    max_bytes: int = 512_000,
) -> dict[str, Any]:
    """
    Returns ``{"ok": bool, "notes": str, "warnings": list[str]}``.
    ``ok`` false blocks apply; warnings are informational for the reviewer UI.
    """
    _ = project_slug  # reserved for contract-aware checks
    warnings: list[str] = []
    rel = str(patch.get("path") or "").strip()
    content = str(patch.get("content") if patch.get("content") is not None else "")

    if not rel.endswith(".md"):
        return {"ok": False, "notes": "only_markdown_paths_allowed", "warnings": []}
    if ".." in rel or rel.startswith(("/", "\\")):
        return {"ok": False, "notes": "path_traversal_or_absolute", "warnings": []}
    try:
        target = (child / rel).resolve()
        target.relative_to(child.resolve())
    except ValueError:
        return {"ok": False, "notes": "path_escapes_repository", "warnings": []}

    raw = content.encode("utf-8", errors="replace")
    if len(raw) > max_bytes:
        return {"ok": False, "notes": f"content_exceeds_{max_bytes}_bytes", "warnings": []}

    fence = content.count("```")
    if fence % 2 != 0:
        warnings.append("odd_number_of_markdown_fences")

    if "```mermaid" in content.lower():
        open_b = content.lower().count("```mermaid")
        if open_b > 3:
            warnings.append("many_mermaid_blocks")

    notes = "precheck_passed" + (f"; warnings={','.join(warnings)}" if warnings else "")
    return {"ok": True, "notes": notes, "warnings": warnings}
