"""Tests for deterministic recheck status engine and recommendations."""

from __future__ import annotations

from lenses.blueprints_wizard.artifact_generation_normalize import QUALITY_DIMENSIONS
from lenses.blueprints_wizard.recheck_status_engine import (
    build_recheck_report,
    list_blocking_upstream_keys,
    transitive_downstream,
)


def _quality_ok() -> dict:
    return {d: {"score": 0.8, "rationale": "ok"} for d in QUALITY_DIMENSIONS}


def _fb_final() -> dict:
    return {
        "content": {"markdown": "# brief"},
        "quality": _quality_ok(),
        "review_status": "approved",
        "locked": False,
        "feedback": "",
        "provenance": {
            "generation_id": "g-fb",
            "created_at": "",
            "provider": "m",
            "model": "",
            "input_fingerprint": "",
            "parent_generation_id": "",
            "lineage": {"upstream": []},
        },
    }


def _roadmap_rec(gen: str, lineage_upstream: list | None = None) -> dict:
    prov = {
        "generation_id": gen,
        "created_at": "2024-01-01T00:00:00Z",
        "provider": "m",
        "model": "",
        "input_fingerprint": "",
        "parent_generation_id": "",
    }
    if lineage_upstream is not None:
        prov["lineage"] = {"upstream": lineage_upstream}
    return {
        "content": {"summary": "s", "themes": [], "horizons": [], "trace_refs": []},
        "quality": _quality_ok(),
        "review_status": "approved",
        "locked": False,
        "feedback": "",
        "provenance": prov,
    }


def test_report_missing_and_present() -> None:
    arts: dict = {}
    rep = build_recheck_report(arts)
    assert rep["schema_version"] == 1
    by_key = {r["artifact_key"]: r for r in rep["artifacts"]}
    assert by_key["roadmap"]["primary_label"] == "missing"
    assert by_key["foundation_brief_final"]["primary_label"] == "missing"


def test_report_stale_lineage() -> None:
    arts = {
        "foundation_brief_final": _fb_final(),
        "roadmap": _roadmap_rec("g-new"),
        "prd": {
            "content": {
                "summary": "p",
                "goals": "",
                "personas": "",
                "scope_in": "",
                "scope_out": "",
                "user_stories": [],
                "trace_refs": [],
            },
            "quality": _quality_ok(),
            "review_status": "pending",
            "locked": False,
            "feedback": "",
            "provenance": {
                "generation_id": "g-prd",
                "created_at": "",
                "provider": "m",
                "model": "",
                "input_fingerprint": "",
                "parent_generation_id": "",
                "lineage": {
                    "upstream": [
                        {"artifact_key": "roadmap", "generation_id": "g-old", "review_status": "approved"},
                    ]
                },
            },
        },
    }
    rep = build_recheck_report(arts)
    by_key = {r["artifact_key"]: r for r in rep["artifacts"]}
    assert by_key["prd"]["primary_label"] == "stale"
    assert any("lineage_drift" in x for x in by_key["prd"]["reasons"])


def test_blocking_upstream_keys_prd() -> None:
    arts: dict = {}
    keys = list_blocking_upstream_keys("prd", arts)
    assert "foundation_brief_final" in keys or "roadmap" in keys


def test_transitive_downstream_from_stale() -> None:
    # roadmap -> milestone_charters (upstream roadmap); prd depends on roadmap
    seed = frozenset({"roadmap"})
    down = transitive_downstream(seed)
    assert "milestone_charters" in down or "prd" in down


def test_recommendations_include_regenerate_closure() -> None:
    arts = {
        "foundation_brief_final": _fb_final(),
        "roadmap": _roadmap_rec("g-new"),
        "prd": {
            "content": {
                "summary": "p",
                "goals": "",
                "personas": "",
                "scope_in": "",
                "scope_out": "",
                "user_stories": [],
                "trace_refs": [],
            },
            "quality": _quality_ok(),
            "review_status": "pending",
            "locked": False,
            "feedback": "",
            "provenance": {
                "generation_id": "g-prd",
                "lineage": {
                    "upstream": [
                        {"artifact_key": "roadmap", "generation_id": "g-old", "review_status": "approved"},
                    ]
                },
            },
        },
    }
    rep = build_recheck_report(arts)
    regen = rep["recommendations"]["regenerate_keys"]
    assert "prd" in regen
    assert "roadmap" in regen or len(regen) >= 1
