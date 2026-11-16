"""Tests for resolve_requested_artifact_keys (planning+engineering vs complete)."""

from __future__ import annotations

from lenses.blueprints_wizard.artifact_generation_dependencies import (
    ENGINEERING_SLICE_KEYS,
    EXECUTION_SLICE_KEYS,
    PLANNING_SLICE_KEYS,
    PLANNING_ENGINEERING_KEYS,
    resolve_requested_artifact_keys,
)
from lenses.blueprints_wizard.artifact_generation_normalize import ARTIFACT_SLICE_KEYS


def test_bundle_all_is_planning_plus_engineering_not_execution() -> None:
    keys, err = resolve_requested_artifact_keys({"artifact_bundle": "all"})
    assert err is None
    assert keys is not None
    assert keys == PLANNING_ENGINEERING_KEYS
    assert EXECUTION_SLICE_KEYS - keys == EXECUTION_SLICE_KEYS


def test_bundle_execution_only() -> None:
    keys, err = resolve_requested_artifact_keys({"artifact_bundle": "execution"})
    assert err is None
    assert keys == EXECUTION_SLICE_KEYS


def test_bundle_complete_is_full_tuple() -> None:
    keys, err = resolve_requested_artifact_keys({"artifact_bundle": "complete"})
    assert err is None
    assert keys == frozenset(ARTIFACT_SLICE_KEYS)


def test_default_bundle_is_planning() -> None:
    keys, err = resolve_requested_artifact_keys({})
    assert err is None
    assert keys == frozenset(PLANNING_SLICE_KEYS)


def test_engineering_bundle() -> None:
    keys, _ = resolve_requested_artifact_keys({"artifact_bundle": "engineering"})
    assert keys == ENGINEERING_SLICE_KEYS
