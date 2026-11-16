"""Remediation scope payload for Docs Health sessions."""

from __future__ import annotations

from pathlib import Path

from lenses.docs_health.remediation_scope import build_remediation_scope


def test_build_remediation_scope_counts_findings_and_rules(tmp_path: Path) -> None:
    (tmp_path / "myproj").mkdir()
    sess = {
        "id": "s1",
        "cluster_id": "c1",
        "cluster": {"label": "API docs"},
        "findings_snapshot": [
            {
                "id": "a",
                "title": "Missing overview",
                "summary": "No top-level API overview.",
                "rule_code": "scope_doc_drift",
                "severity": "medium",
                "affected_paths": ["docs/api.md"],
            },
            {
                "id": "b",
                "title": "Stale link",
                "summary": "Broken relative link.",
                "rule_code": "broken_inventory_link",
                "severity": "low",
                "affected_paths": ["docs/README.md", "docs/api.md"],
            },
        ],
    }
    scope = build_remediation_scope(tmp_path, "myproj", sess)
    assert scope["finding_count"] == 2
    assert scope["distinct_path_count"] == 2
    assert scope["rules_breakdown"].get("scope_doc_drift") == 1
    assert scope["rules_breakdown"].get("broken_inventory_link") == 1
    assert len(scope["sample_findings"]) == 2
    assert "No staged markdown patch" in (scope.get("agent_intent") or "")
    assert scope["cluster_label"] == "API docs"
