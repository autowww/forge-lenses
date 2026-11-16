"""Markdown structure for hybrid comparison report (no LLM)."""

from __future__ import annotations

from lib.file_compare_llm.report_hybrid import render_comparison_report


def test_report_shows_pipeline_error_in_executive_summary():
    merged = {
        "evidence": {"file_a": {}, "file_b": {}, "pairwise": {}},
        "pipeline_error": "pass2 timeout",
        "pass2": None,
        "pass3": None,
    }
    md = render_comparison_report(merged=merged, name_a="A.json", name_b="B.json")
    assert "Incomplete analysis" in md
    assert "pass2 timeout" in md


def test_report_contains_required_sections():
    merged = {
        "evidence": {"file_a": {}, "file_b": {}, "pairwise": {}},
        "pass2": None,
        "pass3": {
            "executive_summary_bullets": ["a", "b"],
            "scorecard": [
                {
                    "dimension_id": "overall",
                    "file_a": 70,
                    "file_b": 65,
                    "winner": "A",
                    "why_it_matters": "Holistic",
                }
            ],
            "what_is_common": ["x"],
            "entity_deltas": [
                {
                    "entity": "e1",
                    "common_ground": "g",
                    "difference": "d",
                    "why_it_matters": "m",
                    "preferred_version": "Tie",
                }
            ],
            "human_bottom_line": "Bottom.",
            "appendix_notes": "",
        },
    }
    md = render_comparison_report(merged=merged, name_a="A.json", name_b="B.json")
    assert "# Comparison report" in md
    assert "## Executive summary" in md
    assert "## Scorecard" in md
    assert "## What is common" in md
    assert "## Material differences" in md
    assert "## Entity-by-entity material deltas" in md
    assert "## Bottom line for a human reviewer" in md
    assert "## Appendix: deterministic evidence" in md
