"""Traceability validation for implementation tasklets."""

from __future__ import annotations

from lenses.blueprints_wizard.artifact_generation_normalize import (
    implementation_tasklets_traceability_ok,
    normalize_artifact_record_content,
)


def test_tasklets_require_upstream_artifact_key() -> None:
    raw = {
        "tasklets": [
            {
                "id": "t1",
                "title": "Work",
                "upstream_artifacts": [{"artifact_key": "prd", "generation_id": ""}],
            }
        ],
        "trace_refs": [],
    }
    content = normalize_artifact_record_content("implementation_tasklets", raw)
    assert implementation_tasklets_traceability_ok(content) is True


def test_tasklets_empty_list_fails() -> None:
    raw = {"tasklets": [], "trace_refs": []}
    content = normalize_artifact_record_content("implementation_tasklets", raw)
    assert implementation_tasklets_traceability_ok(content) is False


def test_tasklets_missing_upstream_fails() -> None:
    raw = {
        "tasklets": [
            {
                "id": "t1",
                "title": "Work",
                "upstream_artifacts": [{"artifact_key": "", "generation_id": "x"}],
            }
        ],
        "trace_refs": [],
    }
    content = normalize_artifact_record_content("implementation_tasklets", raw)
    assert implementation_tasklets_traceability_ok(content) is False
