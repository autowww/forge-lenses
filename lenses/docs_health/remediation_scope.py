"""Structured scope for Docs Health remediation: findings in the cluster vs proposed markdown patch."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from lenses.docs_health.artifacts import session_artifacts_dir
from lenses.docs_health.contract import resolve_project_docs_contract
from lenses.docs_health.diff_util import unified_diff_preview
from lenses.docs_health.repo_md_context import build_repo_md_policy_context
from lenses.registry import load_registry
from lenses.scan import resolve_workspace_child_dir

_LENSES_REPO_ROOT = Path(__file__).resolve().parent.parent.parent


def _truncate(s: str, n: int) -> str:
    t = (s or "").strip()
    if len(t) <= n:
        return t
    return t[: n - 1] + "…"


def _agent_intent_line(kind: str | None, proposed: dict[str, str] | None) -> str:
    if not proposed or not str(proposed.get("path") or "").strip():
        return (
            "No staged markdown patch yet — run a draft step (writer, diagram, or ADR stub) to produce a proposed change."
        )
    p = str(proposed.get("path") or "").strip()
    k = (kind or "").strip().lower()
    if k == "diagram":
        return f"Propose updating {p} with an improved or new diagram (embedded in markdown)."
    if k == "adr":
        return f"Propose adding or updating {p} as an ADR-style decision record."
    if k == "markdown":
        return f"Propose updating {p} with revised or new markdown documentation."
    return f"Propose updating {p} with markdown documentation changes."


def _resolve_child(workspace_root: Path, project_slug: str) -> Path | None:
    reg = load_registry(_LENSES_REPO_ROOT, Path(workspace_root))
    return resolve_workspace_child_dir(Path(workspace_root), project_slug, reg)


def build_remediation_scope(
    workspace_root: Path,
    project_slug: str,
    session: dict[str, Any],
) -> dict[str, Any]:
    """
    Summarize **documentation gaps** (deterministic findings) attached to this session and the **agent's proposed fix**.

    - **finding_count** — how many findings are in this remediation cluster (same scope as the agent's inputs).
    - **rules_breakdown** — counts by ``rule_code`` (categories of gap).
    - **sample_findings** — short examples with titles and paths.
    - **before_after** / **unified_diff_excerpt** — when a patch exists, show old-file excerpt vs new content and/or unified diff.
    """
    raw = session.get("findings_snapshot") if isinstance(session.get("findings_snapshot"), list) else []
    findings: list[dict[str, Any]] = [f for f in raw if isinstance(f, dict)]
    cluster = session.get("cluster") if isinstance(session.get("cluster"), dict) else {}

    paths: set[str] = set()
    rules: dict[str, int] = {}
    samples: list[dict[str, Any]] = []

    for f in findings:
        rc = str(f.get("rule_code") or "").strip() or "unknown"
        rules[rc] = rules.get(rc, 0) + 1
        for ap in f.get("affected_paths") or f.get("affected_files") or []:
            p = str(ap).strip()
            if p:
                paths.add(p)
        if len(samples) < 5:
            aps = f.get("affected_paths") or f.get("affected_files") or []
            samples.append(
                {
                    "id": str(f.get("id") or ""),
                    "title": str(f.get("title") or ""),
                    "summary": _truncate(str(f.get("summary") or f.get("plain_language_summary") or ""), 280),
                    "rule_code": rc,
                    "severity": str(f.get("severity") or ""),
                    "affected_paths": [str(x) for x in aps][:4],
                }
            )

    sid = str(session.get("id") or "").strip()
    proposed = session.get("proposed_patch") if isinstance(session.get("proposed_patch"), dict) else None
    patch_kind = str(session.get("proposed_patch_kind") or "").strip() or None

    diff_excerpt = ""
    if sid:
        try:
            ddir = session_artifacts_dir(workspace_root, project_slug, sid)
            dp = ddir / "diff_preview.patch"
            if dp.is_file():
                diff_excerpt = _truncate(dp.read_text(encoding="utf-8"), 6000)
        except (OSError, ValueError):
            diff_excerpt = ""

    child = _resolve_child(workspace_root, project_slug)
    if proposed and str(proposed.get("path") or "").strip():
        rel = str(proposed.get("path") or "").strip()
        new_content = str(proposed.get("content") if proposed.get("content") is not None else "")
        if not diff_excerpt and child is not None:
            diff_excerpt = _truncate(
                unified_diff_preview(child.resolve(), rel_path=rel, new_content=new_content),
                6000,
            )

    before_after: dict[str, Any] | None = None
    if proposed and str(proposed.get("path") or "").strip():
        rel = str(proposed.get("path") or "").strip()
        new_content = str(proposed.get("content") if proposed.get("content") is not None else "")
        old_snip = ""
        if child is not None:
            p = (child / rel).resolve()
            try:
                p.relative_to(child.resolve())
                if p.is_file():
                    old_snip = _truncate(p.read_text(encoding="utf-8"), 720)
            except (ValueError, OSError):
                old_snip = ""
        if not old_snip.strip():
            old_snip = "(new file, missing path, or file not readable in the project checkout)"
        before_after = {
            "path": rel,
            "before_excerpt": old_snip,
            "after_excerpt": _truncate(new_content, 720),
        }

    rules_sorted = sorted(rules.items(), key=lambda x: (-x[1], x[0]))

    repo_md_context: dict[str, Any] | None = None
    if child is not None and findings:
        contract = resolve_project_docs_contract(child, project_slug=project_slug)
        repo_md_context = build_repo_md_policy_context(child, findings, contract=contract)

    out: dict[str, Any] = {
        "cluster_label": str(cluster.get("label") or "").strip() or None,
        "cluster_id": str(session.get("cluster_id") or "").strip() or None,
        "finding_count": len(findings),
        "distinct_affected_paths": sorted(paths)[:48],
        "distinct_path_count": len(paths),
        "rules_breakdown": {k: v for k, v in rules_sorted},
        "rules_breakdown_list": [{"rule_code": k, "count": v} for k, v in rules_sorted],
        "sample_findings": samples,
        "agent_intent": _agent_intent_line(patch_kind, proposed),
        "proposed_patch_path": str(proposed.get("path") or "").strip() if proposed else None,
        "proposed_patch_kind": patch_kind,
        "unified_diff_excerpt": diff_excerpt.strip() or None,
        "before_after": before_after,
        "note": (
            "Each finding is a deterministic documentation gap from the quality scan; this session works one cluster "
            "at a time. The agent proposes safe markdown-only edits to address those gaps."
        ),
    }
    if repo_md_context is not None:
        out["repo_md_context"] = repo_md_context
    return out


def attach_remediation_scope(workspace_root: Path | Any, project_slug: str, view: dict[str, Any]) -> None:
    """Attach ``remediation_scope`` onto a session payload (mutates in place)."""
    view["remediation_scope"] = build_remediation_scope(Path(workspace_root), str(project_slug), view)
