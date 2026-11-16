"""Tests for artifact_generation normalization."""

from __future__ import annotations

import pytest

from lenses.blueprints_wizard.artifact_generation_normalize import (
    ARTIFACT_GENERATION_SCHEMA_VERSION,
    ARTIFACT_SLICE_KEYS,
    QUALITY_DIMENSIONS,
    merge_artifact_generation_bundle,
    normalize_artifact_generation,
    normalize_provenance,
    normalize_quality_rubric,
)


def test_normalize_quality_rubric_all_dimensions() -> None:
    q = normalize_quality_rubric({"groundedness": {"score": 1.5, "rationale": "x"}})
    assert set(q.keys()) == set(QUALITY_DIMENSIONS)
    assert q["groundedness"]["score"] == 1.0
    assert q["completeness"]["score"] == 0.0


def test_normalize_artifact_generation_empty() -> None:
    ag = normalize_artifact_generation({})
    assert ag["schema_version"] == ARTIFACT_GENERATION_SCHEMA_VERSION
    assert ag["artifacts"] == {}


def test_normalize_provenance_lineage() -> None:
    p = normalize_provenance(
        {
            "generation_id": "g1",
            "lineage": {
                "upstream": [
                    {"artifact_key": "roadmap", "generation_id": "up1", "review_status": "approved"},
                ]
            },
        }
    )
    assert p["lineage"]["upstream"][0]["artifact_key"] == "roadmap"
    assert p["lineage"]["upstream"][0]["generation_id"] == "up1"


def test_merge_partial_preserves_sibling() -> None:
    base = normalize_artifact_generation(
        {
            "artifacts": {
                "foundation_brief_final": {
                    "content": {"markdown": "A"},
                    "quality": {d: {"score": 0.5, "rationale": ""} for d in QUALITY_DIMENSIONS},
                    "review_status": "pending",
                    "locked": False,
                    "feedback": "",
                    "provenance": {"generation_id": "g1", "created_at": ""},
                },
                "roadmap": {
                    "content": {"summary": "S", "themes": [], "horizons": [], "trace_refs": []},
                    "quality": {d: {"score": 0.5, "rationale": ""} for d in QUALITY_DIMENSIONS},
                    "review_status": "pending",
                    "locked": False,
                    "feedback": "",
                    "provenance": {"generation_id": "g2", "created_at": ""},
                },
            }
        }
    )
    incoming = {
        "roadmap": {
            "content": {"summary": "NEW", "themes": [], "horizons": [], "trace_refs": []},
            "quality": {d: {"score": 0.9, "rationale": "r"} for d in QUALITY_DIMENSIONS},
            "review_status": "pending",
            "locked": False,
            "feedback": "",
            "provenance": {"generation_id": "g3", "created_at": "t"},
        }
    }
    merged = merge_artifact_generation_bundle(base, incoming, replace_keys=frozenset({"roadmap"}))
    arts = merged["artifacts"]
    assert "foundation_brief_final" in arts
    assert arts["foundation_brief_final"]["content"]["markdown"] == "A"
    assert arts["roadmap"]["content"]["summary"] == "NEW"


def test_merge_skips_locked() -> None:
    base = normalize_artifact_generation(
        {
            "artifacts": {
                "roadmap": {
                    "content": {"summary": "OLD", "themes": [], "horizons": [], "trace_refs": []},
                    "quality": {d: {"score": 0.5, "rationale": ""} for d in QUALITY_DIMENSIONS},
                    "review_status": "locked",
                    "locked": True,
                    "feedback": "",
                    "provenance": {"generation_id": "x", "created_at": ""},
                }
            }
        }
    )
    incoming = {
        "roadmap": {
            "content": {"summary": "HACK", "themes": [], "horizons": [], "trace_refs": []},
            "quality": {d: {"score": 1.0, "rationale": ""} for d in QUALITY_DIMENSIONS},
            "review_status": "pending",
            "locked": False,
            "feedback": "",
            "provenance": {"generation_id": "y", "created_at": ""},
        }
    }
    merged = merge_artifact_generation_bundle(base, incoming, replace_keys=frozenset({"roadmap"}))
    assert merged["artifacts"]["roadmap"]["content"]["summary"] == "OLD"


@pytest.mark.parametrize("key", list(ARTIFACT_SLICE_KEYS))
def test_slice_keys_in_normalize_map(key: str) -> None:
    assert key in ARTIFACT_SLICE_KEYS
