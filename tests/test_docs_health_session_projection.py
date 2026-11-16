"""Tests for Docs Health session projection helpers."""

from __future__ import annotations

from lenses.docs_health.session_projection import (
    compute_header_stats,
    derive_session_display_name,
    redact_secrets,
    session_public_view,
)


def test_redact_sk_pattern() -> None:
    raw = "token sk-1234567890123456789012345678 end"
    out = redact_secrets(raw)
    assert "sk-1234" not in out
    assert "[REDACTED" in out


def test_redact_bearer() -> None:
    raw = "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.dozjgNryP4J3jVmNHl0w5N_XgL0n3I9PlFUP0THsR8U"
    out = redact_secrets(raw)
    assert "eyJ" not in out


def test_compute_header_stats_counts_and_tokens() -> None:
    sess = {
        "status": "running",
        "started_at": "2020-01-01T00:00:00+00:00",
        "baseline_score": 70,
        "usage_session": {"prompt_tokens": 10, "completion_tokens": 20, "total_tokens": 30},
        "events": [
            {"type": "command", "cmd": "x"},
            {"type": "file_change", "path": "a.md"},
            {"type": "verification", "ok": False, "detail": "fix headings"},
            {"type": "token_stats", "last_model": "demo-model", "snapshot": {}},
            {"type": "kpi_update", "score": 75, "finding_count": 3, "run_id": "r1"},
        ],
    }
    hs = compute_header_stats(sess)
    assert hs["commands_run"] == 1
    assert hs["files_changed"] == 1
    assert hs["total_tokens"] == 30
    assert hs["active_model"] == "demo-model"
    assert hs["verification"] is not None
    assert hs["verification"]["ok"] is False
    assert hs["score_delta"] == 5


def test_session_public_view_includes_header() -> None:
    sess = {"id": "s1", "status": "completed", "events": [], "usage_session": {}}
    pub = session_public_view(sess)
    assert pub["header_stats"]["status"] == "completed"


def test_derive_session_display_name() -> None:
    sess = {
        "project": "my-proj",
        "cluster_id": "c-1",
        "cluster": {"label": "Minor · diagram"},
    }
    assert derive_session_display_name(sess) == "Docs remediation · my-proj · Minor · diagram"


def test_session_public_view_derives_display_name_when_missing() -> None:
    sess = {
        "id": "abc",
        "project": "my-proj",
        "cluster_id": "c-1",
        "cluster": {"label": "Minor · diagram"},
        "status": "running",
        "events": [],
        "usage_session": {},
    }
    pub = session_public_view(sess)
    assert pub.get("display_name") == "Docs remediation · my-proj · Minor · diagram"


def test_session_public_view_preserves_explicit_display_name() -> None:
    sess = {
        "id": "abc",
        "display_name": "Custom runner label",
        "status": "running",
        "events": [],
        "usage_session": {},
    }
    pub = session_public_view(sess)
    assert pub.get("display_name") == "Custom runner label"


def test_compute_header_stats_pipeline_verification() -> None:
    sess = {
        "status": "running",
        "started_at": "2020-01-01T00:00:00+00:00",
        "baseline_score": 80,
        "usage_session": {},
        "events": [
            {"type": "verification", "ok": True, "detail": "links ok", "layer": "pipeline"},
            {"type": "verification", "ok": False, "detail": "model nits", "layer": "model"},
        ],
    }
    hs = compute_header_stats(sess)
    assert hs["verification_pipeline"] is not None
    assert hs["verification_pipeline"]["ok"] is True
    assert hs["verification"] is not None
    assert hs["verification"]["ok"] is False
