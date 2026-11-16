"""Repo Markdown context: deterministic search for policy-style excerpts."""

from __future__ import annotations

from pathlib import Path

from lenses.docs_health.contract import resolve_project_docs_contract
from lenses.docs_health.repo_md_context import build_repo_md_policy_context, collect_query_terms


def test_collect_query_terms_includes_rule_and_policy_vocabulary() -> None:
    terms = collect_query_terms(
        [
            {
                "rule_code": "architecture_diagram",
                "title": "Need diagram",
                "summary": "Visual overview missing.",
            }
        ]
    )
    assert "architecture_diagram" in terms or "architecture" in terms
    assert "diagram" in terms


def test_build_repo_md_finds_prohibition_doc(tmp_path: Path) -> None:
    proj = tmp_path / "demo"
    (proj / "docs").mkdir(parents=True)
    (proj / "docs" / "style.md").write_text(
        "# Documentation style\n\nMermaid diagrams are strictly prohibited. Use SVG or PNG only.\n",
        encoding="utf-8",
    )
    (proj / "README.md").write_text("# Demo\n\nNo diagrams here yet.\n", encoding="utf-8")
    contract = resolve_project_docs_contract(proj, project_slug="demo")
    findings = [
        {
            "id": "x",
            "rule_code": "architecture_diagram",
            "title": "Architecture diagram not detected",
            "summary": "Add a diagram (Mermaid or image).",
            "affected_paths": ["README.md"],
        }
    ]
    ctx = build_repo_md_policy_context(proj, findings, contract=contract)
    hits = ctx.get("hits") or []
    assert hits
    joined = "\n".join(str(h.get("excerpt", "")) for h in hits).lower()
    assert "mermaid" in joined
    paths = {str(h.get("path")) for h in hits}
    assert "docs/style.md" in paths or any("style" in p for p in paths)
