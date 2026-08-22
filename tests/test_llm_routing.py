"""Tests for lenses.llm_routing."""

from __future__ import annotations

from lenses.llm_routing import (
    Complexity,
    ModelTier,
    RequestClassification,
    TaskKind,
    adaptive_adjust,
    pick_from_ordered,
    refinement_shift_toward_cheaper,
)


def test_pick_from_ordered_single() -> None:
    assert pick_from_ordered(["a"], ModelTier.TOP, "x") == "a"


def test_pick_from_ordered_maps_tier() -> None:
    ordered = ["best", "m", "cheap"]
    assert pick_from_ordered(ordered, ModelTier.TOP, "x") == "best"
    assert pick_from_ordered(ordered, ModelTier.EXTRA_LOW, "x") == "cheap"


def test_adaptive_adjust_heavy_reasoning() -> None:
    ordered = ["a", "b", "c", "d", "e", "f"]
    c = RequestClassification(task=TaskKind.REASONING, complexity=Complexity.HEAVY)
    m = adaptive_adjust(ordered, ModelTier.MED, "x", c)
    assert m in ordered


def test_refinement_shift() -> None:
    o = ["a", "b", "c", "d"]
    assert refinement_shift_toward_cheaper(o, "a", 2) == "c"
    assert refinement_shift_toward_cheaper(o, "d", 2) == "d"
