"""Tests for Docs Health closure and suppression overlay."""

from __future__ import annotations

from lenses.docs_health.closure import compute_closure_status, overlay_finding_suppressions


def test_overlay_marks_user_suppressed_by_finding_id() -> None:
    findings = [{"id": "a", "severity": "major"}, {"id": "b", "severity": "minor"}]
    out = overlay_finding_suppressions(
        findings,
        suppressed_finding_ids={"a"},
        suppressed_cluster_ids=set(),
        clusters=None,
    )
    assert out[0]["user_suppressed"] is True
    assert "user_suppressed" not in out[1]


def test_overlay_cluster_suppression() -> None:
    findings = [{"id": "x", "severity": "critical"}, {"id": "y"}]
    clusters = [{"id": "c1", "finding_ids": ["x"]}]
    out = overlay_finding_suppressions(
        findings,
        suppressed_finding_ids=set(),
        suppressed_cluster_ids={"c1"},
        clusters=clusters,
    )
    assert out[0]["user_suppressed"] is True


def test_closure_complete_when_no_hard_severity() -> None:
    findings = [
        {"id": "1", "severity": "minor", "fixability": "auto"},
        {"id": "2", "severity": "major", "fixability": "auto", "user_suppressed": True},
    ]
    st = compute_closure_status(findings, work_items_open=2)
    assert st["complete"] is True
    assert st["open_critical_or_major"] == 0


def test_closure_incomplete_when_major_unsuppressed() -> None:
    findings = [{"id": "1", "severity": "major", "fixability": "ticket_only"}]
    st = compute_closure_status(findings, work_items_open=1)
    assert st["complete"] is False
    assert st["open_critical_or_major"] == 1
