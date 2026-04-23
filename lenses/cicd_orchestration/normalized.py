"""Canonical CI/CD models (provider-agnostic) — Sprint 4.

Normalized objects are plain dicts for JSON APIs. Keys are stable for Studio and classic clients.
"""

from __future__ import annotations

from typing import Any

SCHEMA_VERSION = 1


def empty_control_tower() -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "pipeline_runs": [],
        "environments": [],
        "release_train": None,
        "promotions": [],
        "freeze_windows": [],
        "blocked_promotions": [],
        "what_is_live": [],
        "rollback_targets": [],
    }
