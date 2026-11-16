"""Tests for artifact generation recheck (lineage drift, quality)."""

from __future__ import annotations

from lenses.blueprints_wizard.artifact_generation_normalize import QUALITY_DIMENSIONS
from lenses.blueprints_wizard.artifact_generation_recheck import summarize_artifact_generation_recheck


def _quality_ok() -> dict:
    return {d: {"score": 0.8, "rationale": "ok"} for d in QUALITY_DIMENSIONS}


def test_recheck_passes_minimal_payload() -> None:
    payload = {
        "wizard_domain": {
            "foundation_brief": {"markdown": "x", "field_statuses": {}},
            "run_plan": {"title": "P", "steps": [{"id": "1", "title": "S", "detail": ""}]},
            "artifact_generation": {
                "schema_version": 2,
                "artifacts": {
                    "roadmap": {
                        "content": {"summary": "s", "themes": [], "horizons": [], "trace_refs": []},
                        "quality": _quality_ok(),
                        "review_status": "pending",
                        "locked": False,
                        "feedback": "",
                        "provenance": {
                            "generation_id": "g-road",
                            "created_at": "",
                            "provider": "m",
                            "model": "",
                            "input_fingerprint": "",
                            "parent_generation_id": "",
                            "lineage": {"upstream": []},
                        },
                    }
                },
            },
        },
        "foundation_brief": "x",
    }
    s = summarize_artifact_generation_recheck(payload)
    assert s.get("passed") is True
    assert not s.get("issues")


def test_recheck_lineage_drift() -> None:
    payload = {
        "wizard_domain": {
            "foundation_brief": {"markdown": "x", "field_statuses": {}},
            "run_plan": {"title": "P", "steps": [{"id": "1", "title": "S", "detail": ""}]},
            "artifact_generation": {
                "schema_version": 2,
                "artifacts": {
                    "roadmap": {
                        "content": {"summary": "s", "themes": [], "horizons": [], "trace_refs": []},
                        "quality": _quality_ok(),
                        "review_status": "approved",
                        "locked": False,
                        "feedback": "",
                        "provenance": {
                            "generation_id": "g-new-road",
                            "lineage": {"upstream": []},
                        },
                    },
                    "prd": {
                        "content": {"summary": "p", "goals": "", "personas": "", "scope_in": "", "scope_out": "", "user_stories": [], "trace_refs": []},
                        "quality": _quality_ok(),
                        "review_status": "pending",
                        "locked": False,
                        "feedback": "",
                        "provenance": {
                            "generation_id": "g-prd",
                            "lineage": {
                                "upstream": [
                                    {
                                        "artifact_key": "roadmap",
                                        "generation_id": "g-old-road",
                                        "review_status": "approved",
                                    }
                                ]
                            },
                        },
                    },
                },
            },
        },
        "foundation_brief": "x",
    }
    s = summarize_artifact_generation_recheck(payload)
    issues = list(s.get("issues") or [])
    assert any("lineage_drift" in i for i in issues)
