"""Tests for environment health aggregation."""

from __future__ import annotations

from lenses.environment_health.aggregate import rollup_environment_health


def test_rollup_down_when_probe_fails():
    out = rollup_environment_health([{"ok": False, "status": "down", "url": "http://x"}])
    assert out["status"] == "down"
