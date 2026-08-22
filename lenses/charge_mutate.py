"""Preserve GFM tables while mutating Epic rows on forge/charge.md."""

from __future__ import annotations

import re
import shutil
from pathlib import Path

from lenses.forge_spine import parse_charge_epics
from lenses.roadmap_outline import iter_gfm_tables

_EPIC_ID_RE = re.compile(r"\b(M\d+E\d+)\b", re.I)
_TASK_ROW_RE = re.compile(r"^M\d+E\d+S\d+T\d+$", re.I)


def _slugify_epic(epic_id: str) -> str:
    return epic_id.lower().replace("e", "-e", 1) if epic_id.upper().startswith("M") else epic_id.lower()


def upsert_epic_on_charge(
    charge_path: Path,
    *,
    epic_id: str,
    change_slug: str,
    status: str,
    actor: str,
    wbs_rel: str,
) -> None:
    eid = epic_id.strip().upper()
    if _TASK_ROW_RE.match(eid):
        raise ValueError("Refusing to write Task id as Epic Charge row")
    text = charge_path.read_text(encoding="utf-8", errors="replace")
    rows = parse_charge_epics(text)
    for r in rows:
        if str(r.get("epic_id")).upper() == eid:
            text = _replace_epic_row(text, eid, change_slug, status, actor, wbs_rel)
            charge_path.write_text(text, encoding="utf-8")
            return
    text = _ensure_active_epics_section(text)
    text = _append_epic_row(text, eid, change_slug, status, actor, wbs_rel)
    charge_path.write_text(text, encoding="utf-8")


def remove_epic_from_charge(charge_path: Path, epic_id: str) -> None:
    eid = epic_id.strip().upper()
    text = charge_path.read_text(encoding="utf-8", errors="replace")
    lines = text.splitlines()
    out: list[str] = []
    skip_next_empty = False
    for line in lines:
        if "|" in line and eid in line.upper():
            m = _EPIC_ID_RE.search(line)
            if m and m.group(1).upper() == eid:
                skip_next_empty = True
                continue
        if skip_next_empty and not line.strip():
            skip_next_empty = False
            continue
        out.append(line)
    charge_path.write_text("\n".join(out) + ("\n" if text.endswith("\n") else ""), encoding="utf-8")


def set_epic_charge_status(charge_path: Path, epic_id: str, status: str) -> None:
    eid = epic_id.strip().upper()
    text = charge_path.read_text(encoding="utf-8", errors="replace")
    lines = text.splitlines()
    out: list[str] = []
    for line in lines:
        if "|" in line and eid in line.upper():
            m = _EPIC_ID_RE.search(line)
            if m and m.group(1).upper() == eid:
                parts = [p.strip() for p in line.split("|")]
                if len(parts) >= 6:
                    parts[4] = f" {status} "
                    line = "|".join(parts)
        out.append(line)
    charge_path.write_text("\n".join(out) + ("\n" if text.endswith("\n") else ""), encoding="utf-8")


def _ensure_active_epics_section(text: str) -> str:
    if "## Active Epics" in text:
        return text
    insert = (
        "\n## Active Epics\n\n"
        "| # | id | OpenSpec change | status | actor |\n"
        "|---|-----|-----------------|--------|-------|\n"
    )
    if "## Blockers" in text:
        return text.replace("## Blockers", insert + "\n## Blockers", 1)
    return text.rstrip() + insert


def _append_epic_row(
    text: str,
    epic_id: str,
    change_slug: str,
    status: str,
    actor: str,
    wbs_rel: str,
) -> str:
    n = len(parse_charge_epics(text)) + 1
    row = (
        f"| {n} | [{epic_id}]({wbs_rel}) | "
        f"[{change_slug}](../openspec/changes/{change_slug}/) | {status} | {actor} |"
    )
    lines = text.splitlines()
    out: list[str] = []
    inserted = False
    for i, line in enumerate(lines):
        out.append(line)
        if not inserted and line.strip() == "## Active Epics":
            j = i + 1
            while j < len(lines) and not lines[j].strip().startswith("|"):
                out.append(lines[j])
                j += 1
            if j < len(lines) and lines[j].strip().startswith("|---"):
                out.append(lines[j])
                j += 1
            while j < len(lines) and lines[j].strip().startswith("|"):
                out.append(lines[j])
                j += 1
            out.append(row)
            inserted = True
            while j < len(lines):
                out.append(lines[j])
                j += 1
            break
    if not inserted:
        out.append(row)
    return "\n".join(out) + ("\n" if text.endswith("\n") else "")


def _replace_epic_row(
    text: str,
    epic_id: str,
    change_slug: str,
    status: str,
    actor: str,
    wbs_rel: str,
) -> str:
    lines = text.splitlines()
    out: list[str] = []
    for line in lines:
        if "|" in line and epic_id.upper() in line.upper():
            m = _EPIC_ID_RE.search(line)
            if m and m.group(1).upper() == epic_id.upper():
                num_m = re.match(r"^\|\s*(\d+)\s*\|", line)
                num = num_m.group(1) if num_m else "1"
                line = (
                    f"| {num} | [{epic_id}]({wbs_rel}) | "
                    f"[{change_slug}](../openspec/changes/{change_slug}/) | {status} | {actor} |"
                )
        out.append(line)
    return "\n".join(out) + ("\n" if text.endswith("\n") else "")


def scaffold_openspec_change(repo_base: Path, *, slug: str, epic_id: str) -> Path:
    """Create openspec/changes/<slug>/ from forge-sdlc templates when missing."""
    change_dir = repo_base / "openspec" / "changes" / slug
    if change_dir.is_dir():
        return change_dir
    schema_tpl = repo_base / "openspec" / "schemas" / "forge-sdlc" / "templates"
    change_dir.mkdir(parents=True, exist_ok=True)
    proposal = change_dir / "proposal.md"
    if not proposal.is_file():
        proposal.write_text(
            f"# {slug}\n\n## WBS Epic ID\n\n{epic_id.upper()}\n\n"
            "## Dual wiki\n\n"
            "| In-repo path | Handbook shell | Notes |\n"
            "|--------------|----------------|-------|\n"
            "| | none | Scaffold — declare handbook-bound pages |\n\n"
            "## Why\n\n<!-- Epic intent -->\n\n"
            "## What Changes\n\n<!-- Scope -->\n\n## Capabilities\n\n### New Capabilities\n\n"
            "<!-- capability folders -->\n\n## Impact\n\n<!-- Assay / maintainers -->\n",
            encoding="utf-8",
        )
    for name in ("spec.md", "tasks.md", "design.md"):
        src = schema_tpl / name
        dst = change_dir / name
        if src.is_file() and not dst.is_file():
            shutil.copy2(src, dst)
    specs_dir = change_dir / "specs"
    specs_dir.mkdir(exist_ok=True)
    return change_dir


def archive_openspec_change(repo_base: Path, slug: str) -> None:
    src = repo_base / "openspec" / "changes" / slug
    if not src.is_dir():
        return
    dest_root = repo_base / "openspec" / "changes" / "archive"
    dest_root.mkdir(parents=True, exist_ok=True)
    dest = dest_root / slug
    if dest.exists():
        shutil.rmtree(dest)
    shutil.move(str(src), str(dest))
