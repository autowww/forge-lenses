"""Canonical ops / delivery metrics shell — Sprint 8."""

from __future__ import annotations

from typing import Any

SCHEMA_VERSION = 1


def empty_ops_delivery_overview() -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "services": [],
        "slis": [],
        "slos": [],
        "incidents": [],
        "postmortems": [],
        "error_budget_events": [],
        "feature_flag_exposures": [],
        "dora_metrics": {},
        "rollback_signals": [],
        "postmortem_templates": [],
    }
