"""Fleet client resource gate (CPU / memory vs node ceilings)."""

from __future__ import annotations

from lenses.sandbox import fleet_client as fc


def test_within_limits_no_caps() -> None:
    node = {"max_cpu_percent": None, "max_memory_percent": None}
    health = {"cpu_usage_pct": 99.0, "memory_used_pct": 99.0}
    assert fc._node_within_limits(node, health) is True  # noqa: SLF001


def test_exceeds_cpu() -> None:
    node = {"max_cpu_percent": 50.0, "max_memory_percent": None}
    health = {"cpu_usage_pct": 51.0, "memory_used_pct": 10.0}
    assert fc._node_within_limits(node, health) is False  # noqa: SLF001


def test_exceeds_memory() -> None:
    node = {"max_cpu_percent": None, "max_memory_percent": 80.0}
    health = {"cpu_usage_pct": 10.0, "memory_used_pct": 80.1}
    assert fc._node_within_limits(node, health) is False  # noqa: SLF001


def test_missing_metrics_ignored() -> None:
    node = {"max_cpu_percent": 50.0, "max_memory_percent": 50.0}
    health = {"cpu_usage_pct": None, "memory_used_pct": None}
    assert fc._node_within_limits(node, health) is True  # noqa: SLF001
