#!/usr/bin/env python3
"""Collect Cursor filesystem signals + registry manual metrics → lenses-docs/overview-metrics.json.

Run after build-lenses-docs.py (lenses-docs/ must exist). Invoked from scripts/run-lenses.sh.
"""
from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
OUTPUT_REL = Path("lenses-docs") / "overview-metrics.json"
MAX_TRANSCRIPT_FILES = 500
MAX_LINE_SAMPLE_BYTES = 2 * 1024 * 1024


def _workspace_to_cursor_slug(root: Path) -> str:
    s = str(root.resolve())
    if len(s) > 1 and s[1] == ":" and s[0].isalpha():  # Windows drive
        s = s[2:].lstrip("\\/")
    s = s.strip("/").replace("\\", "/").lstrip("/")
    return s.replace("/", "-")


def _cursor_project_dirs(projects_base: Path, slug: str, mode: str) -> list[Path]:
    if not projects_base.is_dir():
        return []
    out: list[Path] = []
    for p in projects_base.iterdir():
        if not p.is_dir():
            continue
        name = p.name
        if mode == "exact":
            if name == slug:
                out.append(p)
        else:
            if name == slug or name.startswith(slug + "-"):
                out.append(p)
    return sorted(out)


def _scan_agent_transcripts_7d(project_dirs: list[Path], cutoff_ts: float) -> dict:
    session_files = 0
    total_bytes = 0
    lines_sampled = 0
    bytes_sampled = 0
    examined = 0
    capped = False
    for proj in project_dirs:
        at_root = proj / "agent-transcripts"
        if not at_root.is_dir():
            continue
        for session_dir in at_root.iterdir():
            if not session_dir.is_dir():
                continue
            for jsonl in session_dir.glob("*.jsonl"):
                if examined >= MAX_TRANSCRIPT_FILES:
                    capped = True
                    break
                examined += 1
                try:
                    st = jsonl.stat()
                except OSError:
                    continue
                if st.st_mtime < cutoff_ts:
                    continue
                session_files += 1
                total_bytes += st.st_size
                if bytes_sampled < MAX_LINE_SAMPLE_BYTES:
                    try:
                        raw = jsonl.read_bytes()
                    except OSError:
                        continue
                    chunk = raw[: MAX_LINE_SAMPLE_BYTES - bytes_sampled]
                    lines_sampled += chunk.count(b"\n")
                    bytes_sampled += len(chunk)
            if capped:
                break
        if capped:
            break
    return {
        "session_files_7d": session_files,
        "total_bytes_7d": total_bytes,
        "lines_sampled": lines_sampled,
        "transcript_files_examined": examined,
        "transcript_files_capped": capped,
    }


def _scan_workspace_dot_cursor(workspace: Path) -> dict:
    cur = workspace / ".cursor"
    if not cur.is_dir():
        return {
            "present": False,
            "rules_count": 0,
            "skills_count": 0,
            "mcp_present": False,
            "rule_names": [],
        }
    rules_dir = cur / "rules"
    rule_names: list[str] = []
    if rules_dir.is_dir():
        for p in sorted(rules_dir.glob("*.mdc")):
            rule_names.append(p.name)
    skills = list(cur.rglob("SKILL.md"))
    mcp = cur / "mcp.json"
    return {
        "present": True,
        "rules_count": len(rule_names),
        "skills_count": len(skills),
        "mcp_present": mcp.is_file(),
        "rule_names": rule_names[:30],
    }


def main() -> int:
    sys.path.insert(0, str(REPO_ROOT))
    from lenses.registry import load_registry  # noqa: E402

    workspace = Path(
        os.environ.get("LENSES_WORKSPACE_ROOT", str(REPO_ROOT.parent))
    ).resolve()

    out_path = REPO_ROOT / OUTPUT_REL
    out_path.parent.mkdir(parents=True, exist_ok=True)

    generated_at = datetime.now(timezone.utc).isoformat()
    base: dict = {
        "generated_at": generated_at,
        "workspace_root": str(workspace),
        "errors": [],
        "skipped": False,
    }

    if os.environ.get("LENSES_SKIP_CURSOR_METRICS", "").strip().lower() in (
        "1",
        "true",
        "yes",
    ):
        base["skipped"] = True
        base["skip_reason"] = "LENSES_SKIP_CURSOR_METRICS"
        reg = load_registry(REPO_ROOT, workspace)
        manual = reg.get("overview_metrics_manual")
        base["manual"] = manual if isinstance(manual, dict) else {}
        out_path.write_text(json.dumps(base, indent=2), encoding="utf-8")
        print(f"[lenses] overview metrics skipped → {out_path}")
        return 0

    slug = _workspace_to_cursor_slug(workspace)
    mode = os.environ.get("LENSES_CURSOR_PROJECTS_MODE", "prefix").strip().lower()
    if mode not in ("exact", "prefix"):
        mode = "prefix"
    base["cursor_project_slug"] = slug
    base["cursor_projects_mode"] = mode

    projects_base = Path.home() / ".cursor" / "projects"
    try:
        matched = _cursor_project_dirs(projects_base, slug, mode)
        base["cursor_projects_matched"] = [p.name for p in matched]
        now = datetime.now(timezone.utc).timestamp()
        cutoff = now - 7 * 86400
        base["cursor_agents_7d"] = _scan_agent_transcripts_7d(matched, cutoff)
        base["cursor_agents_7d"]["note"] = (
            "Sessions counted by transcript .jsonl file mtime in the last 7 days; not wall-clock duration."
        )
    except OSError as e:
        base["errors"].append(f"cursor_projects: {e}")
        base["cursor_agents_7d"] = {}

    try:
        base["cursor_workspace"] = _scan_workspace_dot_cursor(workspace)
    except OSError as e:
        base["errors"].append(f"workspace_dot_cursor: {e}")
        base["cursor_workspace"] = {"present": False, "error": str(e)}

    try:
        reg = load_registry(REPO_ROOT, workspace)
        manual = reg.get("overview_metrics_manual")
        base["manual"] = manual if isinstance(manual, dict) else {}
    except OSError as e:
        base["errors"].append(f"registry: {e}")
        base["manual"] = {}

    out_path.write_text(json.dumps(base, indent=2), encoding="utf-8")
    print(f"[lenses] overview metrics → {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
