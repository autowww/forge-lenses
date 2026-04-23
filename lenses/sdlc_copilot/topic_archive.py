"""Append-only topic wrap-up for Copilot (JSONL + Markdown snapshot under .lenses-local/)."""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

_TOPICS_FILE = "copilot-topics.jsonl"
_DISCUSSIONS_DIR = "copilot-discussions"
_MAX_LINE = 120_000


def _safe_slug(s: str, max_len: int = 48) -> str:
    t = re.sub(r"[^a-zA-Z0-9._-]+", "-", (s or "").strip().lower()).strip("-")
    return (t[:max_len] if t else "topic")


def topics_log_path(workspace_root: Path) -> Path:
    return workspace_root.resolve() / ".lenses-local" / _TOPICS_FILE


def discussions_dir(workspace_root: Path) -> Path:
    d = workspace_root.resolve() / ".lenses-local" / _DISCUSSIONS_DIR
    d.mkdir(parents=True, exist_ok=True)
    return d


def archive_copilot_topic(workspace_root: Path, body: dict[str, Any]) -> dict[str, Any]:
    """Persist a wrapped-up Copilot topic from the browser (truncated excerpts)."""
    root = workspace_root.resolve()
    topic_id = str(body.get("topic_id") or "").strip() or "topic"
    started = str(body.get("started_at_iso") or "").strip()
    ended = str(body.get("ended_at_iso") or "").strip() or datetime.now(timezone.utc).isoformat()
    route = str(body.get("route") or "").strip()[:200]
    project_slug = body.get("project_slug")
    ps = str(project_slug).strip()[:200] if project_slug is not None else ""
    turns = body.get("turns")
    if not isinstance(turns, list):
        turns = []
    tags = body.get("tags")
    if not isinstance(tags, list):
        tags = []
    tags_s = [str(t).strip()[:120] for t in tags if str(t).strip()][:24]

    totals = body.get("totals") if isinstance(body.get("totals"), dict) else {}
    summary = str(body.get("summary") or "").strip()[:4000]
    title = str(body.get("title") or "").strip()[:240]

    event: dict[str, Any] = {
        "kind": "copilot_topic_wrap",
        "topic_id": topic_id[:120],
        "started_at_iso": started[:80] or None,
        "ended_at_iso": ended[:80],
        "route": route or None,
        "project_slug": ps or None,
        "turn_count": len(turns),
        "tags": tags_s or None,
        "totals": totals,
        "title": title or None,
        "summary": summary or None,
    }

    p = topics_log_path(root)
    p.parent.mkdir(parents=True, exist_ok=True)
    line = json.dumps(event, ensure_ascii=False, sort_keys=True) + "\n"
    if len(line) > _MAX_LINE:
        slim = {k: event[k] for k in ("kind", "topic_id", "ended_at_iso", "turn_count") if k in event}
        line = json.dumps(slim, ensure_ascii=False, sort_keys=True) + "\n"
    with p.open("a", encoding="utf-8") as f:
        f.write(line)
    try:
        p.chmod(0o600)
    except OSError:
        pass

    slug = _safe_slug(f"{route}-{topic_id[:8]}")
    md_name = f"{ended[:10]}_{slug}.md"
    md_path = discussions_dir(root) / md_name
    lines: list[str] = [
        "---",
        f'title: "{title or "Copilot topic"}"',
        f"topic_id: {topic_id}",
        f"ended_at: {ended}",
        f"route: {route or 'unknown'}",
        "tags:",
    ]
    for t in tags_s:
        lines.append(f"  - {t}")
    lines.extend(["---", "", "## Summary", summary or "(no summary provided)", "", "## Turns (excerpts)", ""])
    for i, row in enumerate(turns[:80]):
        if not isinstance(row, dict):
            continue
        role = str(row.get("role") or "?")[:20]
        excerpt = str(row.get("text_excerpt") or "").strip()[:2000]
        usage = row.get("usage")
        uline = ""
        if isinstance(usage, dict):
            uline = f" _tokens: {usage.get('total_tokens')}_"
        lines.append(f"### {i + 1}. {role}{uline}")
        lines.append("")
        lines.append(excerpt or "_(empty)_")
        lines.append("")
    try:
        md_path.write_text("\n".join(lines), encoding="utf-8")
        md_path.chmod(0o600)
    except OSError:
        return {"ok": True, "topics_log": str(p.relative_to(root)), "markdown": None}

    return {
        "ok": True,
        "topics_log": str(p.relative_to(root)),
        "markdown": str(md_path.relative_to(root)),
    }
