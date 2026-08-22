"""Parse blueprint-style WBS.md into themes, epics, stories, and tasks (ID spine)."""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from lenses.roadmap_outline import _parse_pipe_table_rows

HEADING_RE = re.compile(r"^(#{2,6})\s+(.+?)\s*$")

# M1E1S1, M1E1S1T1 (story / task)
WBS_ID_RE = re.compile(r"\b(M\d+E\d+S\d+(?:T\d+)?)\b")
BACKTICK_PATH_RE = re.compile(r"`([^`]+\.(?:md|mdc|yaml|yml|json))`")


def _norm_header(h: str) -> str:
    return re.sub(r"\s+", " ", h.strip().lower())


def _find_col(hdr: list[str], *needles: str) -> int | None:
    nh = [_norm_header(c) for c in hdr]
    for i, h in enumerate(nh):
        for n in needles:
            if n in h or h == n:
                return i
    return None


def _extract_paths(cell: str) -> list[str]:
    return [m.group(1) for m in BACKTICK_PATH_RE.finditer(cell or "")]


def _wbs_ids_in_cell(cell: str) -> list[str]:
    """Ordered unique WBS id tokens (stories or tasks) from a table cell."""
    seen: set[str] = set()
    out: list[str] = []
    for m in WBS_ID_RE.finditer(cell or ""):
        w = m.group(1)
        if w not in seen:
            seen.add(w)
            out.append(w)
    return out


def _split_blockers_cell(cell: str) -> list[str]:
    out: list[str] = []
    for part in re.split(r"[,;\n]+", cell or ""):
        p = part.strip()
        if p:
            out.append(p)
    return out


@dataclass
class WbsTask:
    id: str
    title: str
    story_id: str
    row: dict[str, str] = field(default_factory=dict)
    blockers: list[str] = field(default_factory=list)


@dataclass
class WbsStory:
    id: str
    title: str
    theme_label: str
    epic_label: str
    acceptance_summary: str
    product_paths: list[str]
    dependencies: list[str] = field(default_factory=list)
    priority: str = ""
    row: dict[str, str] = field(default_factory=dict)
    tasks: list[WbsTask] = field(default_factory=list)


@dataclass
class WbsModel:
    rel_path: str
    themes: list[tuple[str, str]] = field(default_factory=list)  # (id_or_label, heading)
    epics: list[tuple[str, str, str]] = field(default_factory=list)  # (epic_key, heading, theme_label)
    stories: dict[str, WbsStory] = field(default_factory=dict)
    tasks: dict[str, WbsTask] = field(default_factory=dict)
    # Prose under a "## Milestone M1 …" (or ###) heading until the next heading of same/higher level.
    milestone_outcomes: dict[str, str] = field(default_factory=dict)


def _table_kind(hdr: list[str]) -> str | None:
    joined = " ".join(_norm_header(c) for c in hdr)
    if "story id" in joined or (joined.startswith("story") and "id" in joined):
        return "story"
    if "task id" in joined or (joined.startswith("task") and "id" in joined):
        return "task"
    return None


def _story_columns(hdr: list[str]) -> tuple[int | None, int | None]:
    nh = [_norm_header(c) for c in hdr]
    idx_id: int | None = None
    for i, h in enumerate(nh):
        if "story id" in h or h == "story id":
            idx_id = i
            break
    if idx_id is None:
        for i, h in enumerate(nh):
            if h.startswith("story") and "id" in h:
                idx_id = i
                break
    idx_title: int | None = None
    for i, h in enumerate(nh):
        if idx_id is not None and i == idx_id:
            continue
        if h == "story" or (h.startswith("story") and "id" not in h):
            idx_title = i
            break
    if idx_title is None and idx_id is not None and len(nh) > idx_id + 1:
        idx_title = idx_id + 1
    return idx_id, idx_title


def _parse_story_table(
    table: list[list[str]],
    theme_label: str,
    epic_label: str,
    out: WbsModel,
) -> None:
    if len(table) < 2:
        return
    hdr = table[0]
    kind = _table_kind(hdr)
    if kind != "story":
        return
    idx_id, idx_title = _story_columns(hdr)
    if idx_id is None:
        idx_id = 0
    ac_idx = _find_col(
        hdr,
        "acceptance",
        "criteria",
        "acceptance criteria",
    )
    dep_idx = _find_col(hdr, "dependencies", "dependency", "depends", "deps")
    pri_idx = _find_col(hdr, "priority", "prio")
    for row in table[2:]:
        if len(row) < len(hdr):
            row = row + [""] * (len(hdr) - len(row))
        raw_id = (row[idx_id] if idx_id < len(row) else "").strip()
        m = WBS_ID_RE.search(raw_id)
        if not m:
            continue
        sid = m.group(1)
        if "T" in sid and re.search(r"S\d+T\d+", sid):
            continue
        title = ""
        if idx_title is not None and idx_title < len(row):
            title = re.sub(r"\*+", "", row[idx_title]).strip()
        ac = ""
        if ac_idx is not None and ac_idx < len(row):
            ac = row[ac_idx].strip()
        paths: list[str] = []
        for cell in row:
            paths.extend(_extract_paths(cell))
        cells = {hdr[i]: row[i] for i in range(min(len(hdr), len(row)))}
        deps: list[str] = []
        if dep_idx is not None and dep_idx < len(row):
            deps = _wbs_ids_in_cell(row[dep_idx])
        pri = ""
        if pri_idx is not None and pri_idx < len(row):
            pri = re.sub(r"\*+", "", row[pri_idx]).strip()
        out.stories[sid] = WbsStory(
            id=sid,
            title=title,
            theme_label=theme_label,
            epic_label=epic_label,
            acceptance_summary=ac,
            product_paths=sorted(set(paths)),
            dependencies=deps,
            priority=pri,
            row=cells,
        )


def _parse_task_table(
    table: list[list[str]],
    theme_label: str,
    epic_label: str,
    out: WbsModel,
) -> None:
    if len(table) < 2:
        return
    hdr = table[0]
    kind = _table_kind(hdr)
    if kind != "task":
        return
    idx_id = _find_col(hdr, "task id", "task")
    idx_story = _find_col(hdr, "story")
    idx_title = _find_col(hdr, "task", "title")
    if idx_id is None:
        idx_id = 0
    blk_idx = _find_col(hdr, "blockers", "blocker")
    for row in table[2:]:
        if len(row) < len(hdr):
            row = row + [""] * (len(hdr) - len(row))
        raw_id = (row[idx_id] if idx_id < len(row) else "").strip()
        m = WBS_ID_RE.search(raw_id)
        if not m:
            continue
        tid = m.group(1)
        if not tid.endswith("T") and "T" in tid.split("S")[-1]:
            pass  # M1E1S1T1
        title = ""
        if idx_title is not None and idx_title < len(row):
            title = re.sub(r"\*+", "", row[idx_title]).strip()
        story_id = ""
        if idx_story is not None and idx_story < len(row):
            sm = WBS_ID_RE.search(row[idx_story])
            if sm:
                story_id = sm.group(1)
                if "T" in story_id:
                    story_id = re.sub(r"T\d+$", "", story_id)
        cells = {hdr[i]: row[i] for i in range(min(len(hdr), len(row)))}
        blockers: list[str] = []
        if blk_idx is not None and blk_idx < len(row):
            blockers = _split_blockers_cell(row[blk_idx])
        task = WbsTask(
            id=tid, title=title, story_id=story_id, row=cells, blockers=blockers
        )
        out.tasks[tid] = task
        if story_id and story_id in out.stories:
            out.stories[story_id].tasks.append(task)


def _milestone_key_from_heading(title: str) -> str | None:
    """Match standalone milestone id (M1) after the word Milestone, not M1E1."""
    tl = title.lower()
    if "milestone" not in tl:
        return None
    m = re.search(r"(?i)milestone[:\s—-]+(M\d+)\b", title)
    if m:
        return m.group(1)
    m = re.search(r"(?i)\b(M\d+)\s*$", title.strip())
    if m and not re.search(r"M\d+E", title):
        return m.group(1)
    return None


def parse_wbs_markdown(rel_path: str, md: str) -> WbsModel:
    out = WbsModel(rel_path=rel_path)
    lines = md.splitlines()
    current_theme = ""
    current_epic = ""
    i = 0
    while i < len(lines):
        line = lines[i]
        hm = HEADING_RE.match(line)
        if hm:
            level = len(hm.group(1))
            title = hm.group(2).strip()
            tl = title.lower()
            mk = _milestone_key_from_heading(title)
            if mk and level <= 4:
                j = i + 1
                body_lines: list[str] = []
                while j < len(lines):
                    ln = lines[j]
                    inner = HEADING_RE.match(ln)
                    if inner:
                        il = len(inner.group(1))
                        itl = inner.group(2).strip().lower()
                        if il <= level:
                            break
                        if "epic:" in itl and il <= 4:
                            break
                    body_lines.append(ln)
                    j += 1
                prose = "\n".join(body_lines).strip()
                if prose:
                    out.milestone_outcomes[mk] = prose
                i = j
                continue
            if "theme" in tl and level <= 4:
                m = re.search(r"\b(T\d+)\b", title)
                current_theme = m.group(1) if m else title
                out.themes.append((current_theme, title))
            if "epic:" in tl and level <= 4:
                m = re.search(r"\b(M\d+E\d+)\b", title)
                ek = m.group(1) if m else title
                current_epic = title
                out.epics.append((ek, title, current_theme))
            i += 1
            continue
        if "|" in line and line.strip().startswith("|"):
            block: list[str] = []
            j = i
            while j < len(lines) and "|" in lines[j]:
                block.append(lines[j])
                j += 1
            parsed = _parse_pipe_table_rows(block)
            if parsed and len(parsed) >= 2:
                _parse_story_table(parsed, current_theme, current_epic, out)
                _parse_task_table(parsed, current_theme, current_epic, out)
            i = j
            continue
        i += 1

    for tid, task in out.tasks.items():
        sid = task.story_id
        if not sid:
            sm = WBS_ID_RE.search(tid)
            if sm:
                raw = sm.group(1)
                if "T" in raw:
                    sid = re.sub(r"T\d+$", "", raw)
        if sid and sid in out.stories:
            if task not in out.stories[sid].tasks:
                out.stories[sid].tasks.append(task)

    for st in out.stories.values():
        st.tasks.sort(key=lambda t: t.id)
    return out


