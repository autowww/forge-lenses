"""Canonical cross-team release models — Sprint 7."""

from __future__ import annotations

from typing import Any

SCHEMA_VERSION = 1


def empty_cross_team_overview() -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "dependency_board": {"nodes": [], "edges": []},
        "release_calendar": {"events": []},
        "change_requests": [],
        "cab_sessions": [],
        "go_no_go_packet": {"sections": [], "markdown": ""},
        "communication_artifacts": {
            "release_notes_md": "",
            "stakeholder_summary_md": "",
            "blocker_summary_md": "",
        },
    }
