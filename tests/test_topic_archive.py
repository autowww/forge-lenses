"""Copilot topic archive (local files)."""

from __future__ import annotations

from pathlib import Path

from lenses.sdlc_copilot.topic_archive import archive_copilot_topic, topics_log_path


def test_archive_topic_writes_jsonl(tmp_path: Path) -> None:
    r = archive_copilot_topic(
        tmp_path,
        {
            "topic_id": "tid-1",
            "started_at_iso": "2026-01-01T00:00:00Z",
            "ended_at_iso": "2026-01-01T00:05:00Z",
            "route": "overview",
            "turns": [{"role": "user", "text_excerpt": "hi"}],
            "tags": ["route:overview"],
            "title": "Test",
            "summary": "One turn.",
            "totals": {"dwell_approx_sec": 12},
        },
    )
    assert r.get("ok") is True
    p = topics_log_path(tmp_path)
    assert p.is_file()
    text = p.read_text(encoding="utf-8").strip().splitlines()[-1]
    assert "copilot_topic_wrap" in text
    assert "tid-1" in text
