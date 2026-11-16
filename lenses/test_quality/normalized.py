"""Canonical test / quality models (Sprint 5) — JSON-friendly dicts."""

from __future__ import annotations

from typing import Any

SCHEMA_VERSION = 1


def empty_quality_overview() -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "test_plans": [],
        "test_suites": [],
        "test_cases": [],
        "test_runs": [],
        "defects": [],
        "coverage_summaries": [],
        "flaky_test_signals": [],
        "quality_gates": [],
        "gate_evaluations": [],
        "uat_signoffs": [],
        "regression_packs": [],
        "release_readiness_checklists": [],
        "evidence_attachments": [],
        "release_quality": None,
        "run_comparisons": [],
    }
