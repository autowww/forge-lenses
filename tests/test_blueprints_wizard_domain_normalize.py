"""Tests for wizard_domain normalization (experimental Blueprints Wizard)."""

from __future__ import annotations

import pytest

from lenses.blueprints_wizard.schemas import normalize_wizard_payload
from lenses.blueprints_wizard.wizard_domain_normalize import (
    empty_wizard_domain,
    normalize_wizard_domain,
)


def test_empty_wizard_domain_schema_version() -> None:
    d = empty_wizard_domain()
    assert d["schema_version"] == 1
    assert d["mission_type"] == "explore"
    assert d["contribution_setup_kind"] == "single"
    assert d["prompt_snapshot"] is None


def test_invalid_enums_coerce_to_defaults() -> None:
    raw = {
        "schema_version": 1,
        "mission_type": "not_a_real_mission",
        "contribution_setup_kind": "mega",
        "target_stage": "nope",
        "autonomy_level": "???",
        "mutation_policy": "delete_everything",
        "context_sources": ["repo", "invalid_source"],
    }
    out = normalize_wizard_domain(raw)
    assert out["mission_type"] == "explore"
    assert out["contribution_setup_kind"] == "single"
    assert out["target_stage"] == "idea"
    assert out["autonomy_level"] == "l0_analyst"
    assert out["mutation_policy"] == "read_only_analysis"
    assert out["context_sources"] == ["repo", "other"]


def test_legacy_target_stage_maps() -> None:
    out = normalize_wizard_domain({"target_stage": "discovery"})
    assert out["target_stage"] == "idea"


def test_legacy_autonomy_mutation_maps() -> None:
    out = normalize_wizard_domain({"autonomy_level": "suggest_only", "mutation_policy": "read_only"})
    assert out["autonomy_level"] == "l0_analyst"
    assert out["mutation_policy"] == "read_only_analysis"


def test_scope_spec_closure_options_normalized() -> None:
    from lenses.blueprints_wizard.wizard_domain_normalize import normalize_scope_spec

    s = normalize_scope_spec(
        {"closure_options": ["include_verification_artifacts", "exact_only", "exact_only"]}
    )
    assert s["closure_options"] == ["exact_only", "include_verification_artifacts"]


def test_unknown_top_level_key_preserved() -> None:
    raw = {"future_flag": {"x": 1}, "mission_type": "deliver"}
    out = normalize_wizard_domain(raw)
    assert out["future_flag"] == {"x": 1}
    assert out["mission_type"] == "deliver"


def test_normalize_wizard_payload_includes_wizard_domain() -> None:
    pl = normalize_wizard_payload({"title": "T"})
    assert "wizard_domain" in pl
    assert pl["wizard_domain"]["mission_type"] == "explore"


def test_assumption_ledger_entry_status_round_trip() -> None:
    from lenses.blueprints_wizard.wizard_domain_normalize import normalize_assumption_ledger_entry

    e = normalize_assumption_ledger_entry(
        {"id": "x", "text": "hello", "status": "resolved", "source": "stakeholders"}
    )
    assert e is not None
    assert e["status"] == "resolved"


def test_normalize_wizard_payload_merges_existing_domain() -> None:
    pl = normalize_wizard_payload(
        {
            "wizard_domain": {
                "mission_type": "operate",
                "assumption_ledger": [{"id": "a1", "text": "Assume X"}],
            }
        }
    )
    wd = pl["wizard_domain"]
    assert wd["mission_type"] == "operate"
    assert len(wd["assumption_ledger"]) == 1
    assert wd["assumption_ledger"][0]["id"] == "a1"


def test_round_trip_deepcopy() -> None:
    a = empty_wizard_domain()
    b = normalize_wizard_domain(a)
    a["mission_type"] = "sunset"
    assert b["mission_type"] == "explore"


@pytest.mark.parametrize("sv", [1, 2, "3"])
def test_schema_version_coerce(sv: object) -> None:
    out = normalize_wizard_domain({"schema_version": sv})
    assert out["schema_version"] >= 1
