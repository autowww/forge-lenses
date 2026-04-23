"""Parse ROADMAP.md into sections, tables, and outline JSON for lenses UI."""

from __future__ import annotations

import html
import json
import re
from dataclasses import dataclass, field
from datetime import datetime

HEADING_RE = re.compile(r"^(#{2,6})\s+(.+?)\s*$")
DELIM_ROW_RE = re.compile(r"^\s*\|?[\s\-:|]+\|\s*$")


def _esc(s: str) -> str:
    return html.escape(s, quote=True)


def _slug_base(title: str) -> str:
    t = title.strip().lower()
    t = re.sub(r"[^\w\s-]", "", t)
    t = re.sub(r"[-\s]+", "-", t).strip("-")
    return t or "section"


@dataclass
class RoadmapSection:
    id: str
    level: int
    title: str
    body: str


@dataclass
class ParsedRoadmap:
    doc_title: str
    sections: list[RoadmapSection] = field(default_factory=list)


def _split_sections(md: str) -> tuple[str, list[tuple[int, str, str]]]:
    """Return (doc_title, [(level, title, body), ...]). Body excludes heading line."""
    lines = md.splitlines()
    doc_title = ""
    i = 0
    while i < len(lines) and not lines[i].strip():
        i += 1
    if i < len(lines) and lines[i].startswith("# ") and not lines[i].startswith("##"):
        doc_title = lines[i][2:].strip()
        i += 1

    preamble_lines: list[str] = []
    chunks: list[tuple[int, str, list[str]]] = []
    current_level = 0
    current_title = ""
    current_body: list[str] = []

    def flush_preamble() -> None:
        nonlocal preamble_lines, i
        if preamble_lines:
            body = "\n".join(preamble_lines).strip()
            if body:
                chunks.append((2, "Overview", preamble_lines.copy()))
            preamble_lines = []

    while i < len(lines):
        line = lines[i]
        m = HEADING_RE.match(line)
        if m:
            flush_preamble()
            if current_level and current_title:
                chunks.append((current_level, current_title, current_body))
            current_level = len(m.group(1))
            current_title = m.group(2).strip()
            current_body = []
            i += 1
            continue
        if not chunks and not current_level:
            preamble_lines.append(line)
        else:
            current_body.append(line)
        i += 1

    flush_preamble()
    if current_level and current_title:
        chunks.append((current_level, current_title, current_body))

    out: list[tuple[int, str, str]] = []
    for lev, tit, body_lines in chunks:
        out.append((lev, tit, "\n".join(body_lines).strip()))
    return doc_title, out


def _assign_ids(titled: list[tuple[int, str, str]]) -> list[RoadmapSection]:
    seen: dict[str, int] = {}
    sections: list[RoadmapSection] = []
    for lev, title, body in titled:
        base = _slug_base(title)
        n = seen.get(base, 0) + 1
        seen[base] = n
        sid = base if n == 1 else f"{base}-{n}"
        sections.append(RoadmapSection(id=sid, level=lev, title=title, body=body))
    return sections


def parse_roadmap_markdown(md: str) -> ParsedRoadmap:
    doc_title, chunks = _split_sections(md)
    sections = _assign_ids(chunks)
    return ParsedRoadmap(doc_title=doc_title, sections=sections)


def outline_dict(parsed: ParsedRoadmap) -> dict[str, object]:
    return {
        "doc_title": parsed.doc_title,
        "sections": [
            {"id": s.id, "level": s.level, "title": s.title} for s in parsed.sections
        ],
    }


def outline_json(parsed: ParsedRoadmap) -> str:
    return json.dumps(outline_dict(parsed), indent=2, sort_keys=True)


def _parse_pipe_table_rows(block: list[str]) -> list[list[str]] | None:
    if len(block) < 2:
        return None
    if not DELIM_ROW_RE.match(block[1]):
        return None
    rows: list[list[str]] = []
    for bl in block:
        raw = bl.strip()
        if raw.startswith("|"):
            raw = raw[1:]
        if raw.endswith("|"):
            raw = raw[:-1]
        cells = [c.strip() for c in raw.split("|")]
        rows.append(cells)
    return rows


def iter_gfm_tables(text: str) -> list[list[list[str]]]:
    lines = text.splitlines()
    tables: list[list[list[str]]] = []
    i = 0
    while i < len(lines):
        line = lines[i]
        if "|" in line and line.strip().startswith("|"):
            block: list[str] = []
            j = i
            while j < len(lines) and "|" in lines[j]:
                block.append(lines[j])
                j += 1
            parsed = _parse_pipe_table_rows(block)
            if parsed:
                tables.append(parsed)
            i = j
        else:
            i += 1
    return tables


def _normalize_header(h: str) -> str:
    return re.sub(r"\s+", " ", h.strip().lower())


def extract_chart_metrics(md: str) -> dict[str, object]:
    """Heuristic metrics from all pipe tables in the roadmap."""
    epic_bars: list[tuple[str, float]] = []
    status_counts: dict[str, int] = {}
    horizon_counts: dict[str, int] = {}

    for table in iter_gfm_tables(md):
        if len(table) < 2:
            continue
        hdr = [_normalize_header(c) for c in table[0]]
        if not hdr:
            continue

        def find_col(predicates: tuple[str, ...]) -> int | None:
            for i, h in enumerate(hdr):
                for p in predicates:
                    if p in h or h == p:
                        return i
            return None

        idx_pct = find_col(("% complete", "%", "complete", "percent"))
        idx_status = find_col(("status",))
        idx_horizon = find_col(("horizon", "window"))
        idx_id = find_col(
            ("epic id", "epic", "milestone", "story", "id", "spark", "title")
        )

        for row in table[2:]:
            if len(row) < len(hdr):
                row = row + [""] * (len(hdr) - len(row))

            if idx_horizon is not None and idx_horizon < len(row):
                hz = re.sub(r"\*+", "", row[idx_horizon]).strip().upper()
                if hz in ("NOW", "NEXT", "LATER", "FIRST", "PARALLEL"):
                    horizon_counts[hz] = horizon_counts.get(hz, 0) + 1

            if idx_status is not None and idx_status < len(row):
                st = row[idx_status].strip().lower()
                if st:
                    key = st[:48]
                    status_counts[key] = status_counts.get(key, 0) + 1

            pct_val: float | None = None
            if idx_pct is not None and idx_pct < len(row):
                cell = row[idx_pct].strip().replace("%", "").strip()
                m = re.search(r"(\d+(?:\.\d+)?)", cell)
                if m:
                    try:
                        pct_val = float(m.group(1))
                        pct_val = max(0.0, min(100.0, pct_val))
                    except ValueError:
                        pct_val = None

            label = ""
            if idx_id is not None and idx_id < len(row):
                label = row[idx_id].strip()
            if not label and row:
                label = row[0].strip()[:80]
            if pct_val is not None and label:
                epic_bars.append((label, pct_val))

    has_any = bool(epic_bars or status_counts or horizon_counts)
    return {
        "has_chartable": has_any,
        "epic_bars": epic_bars,
        "status_counts": status_counts,
        "horizon_counts": horizon_counts,
    }


_MILESTONE_ID_RE = re.compile(r"M\s*(\d+)\s*\.\s*(\d+)", re.I)
_EPIC_ID_IN_CELL = re.compile(r"\b(M\d+E\d+)\b")


def _strip_md_noise(s: str) -> str:
    return re.sub(r"\*+", "", s).strip()


def _milestone_key(major: int, minor: int) -> str:
    return f"M{major}.{minor}"


def _parse_leading_milestone_id(cell: str) -> str | None:
    """First M#.# in cell, normalized to M1.2 form."""
    m = _MILESTONE_ID_RE.search(_strip_md_noise(cell))
    if not m:
        return None
    return _milestone_key(int(m.group(1)), int(m.group(2)))


def _milestone_sort_key(mid: str) -> tuple[int, int, str]:
    m = _MILESTONE_ID_RE.search(mid)
    if m:
        return (int(m.group(1)), int(m.group(2)), mid)
    return (9999, 9999, mid)


def _all_milestone_refs_in_cell(cell: str) -> list[str]:
    """Ordered M#.# references found in a horizon/window cell."""
    out: list[str] = []
    seen: set[str] = set()
    for m in _MILESTONE_ID_RE.finditer(_strip_md_noise(cell)):
        k = _milestone_key(int(m.group(1)), int(m.group(2)))
        if k not in seen:
            seen.add(k)
            out.append(k)
    return out


def _is_milestone_schedule_table(hdr: list[str]) -> bool:
    if not hdr:
        return False
    h0 = _normalize_header(hdr[0])
    if "milestone" not in h0:
        return False
    if "epic" in h0:
        return False
    return True


def _is_epic_horizon_table(hdr: list[str]) -> bool:
    if not hdr:
        return False
    joined = " ".join(_normalize_header(c) for c in hdr)
    if "epic" not in joined:
        return False
    hz = False
    for c in hdr:
        n = _normalize_header(c)
        if "horizon" in n or n == "window":
            hz = True
            break
    return hz


def _gantt_find_col(hdr: list[str], predicates: tuple[str, ...]) -> int | None:
    for i, h in enumerate(hdr):
        for p in predicates:
            if p in h or h == p:
                return i
    return None


ISO_DATE_RE = re.compile(r"\b(\d{4}-\d{2}-\d{2})\b")


def _parse_iso_date_str(cell: str) -> str | None:
    m = ISO_DATE_RE.search(_strip_md_noise(cell))
    if not m:
        return None
    s = m.group(1)
    try:
        datetime.strptime(s, "%Y-%m-%d")
    except ValueError:
        return None
    return s


def _is_epic_date_shift_table(hdr: list[str]) -> bool:
    if not hdr:
        return False
    joined = " ".join(_normalize_header(c) for c in hdr)
    if "epic" not in joined:
        return False
    for c in hdr:
        n = _normalize_header(c)
        if (
            "initial start" in n
            or "initial end" in n
            or "target start" in n
            or "target end" in n
        ):
            return True
    return False


def _date_shift_col(hdr: list[str], *needles: str) -> int | None:
    for i, h in enumerate(hdr):
        n = _normalize_header(h)
        for nd in needles:
            if n == nd or nd in n:
                return i
    return None


def extract_date_shift_model(md: str) -> dict[str, object]:
    """
    Epic rows with Initial/Target start/end columns (ISO YYYY-MM-DD).
    Used for baseline vs current plan visualization in Lenses.
    """
    rows_out: list[dict[str, object]] = []
    for table in iter_gfm_tables(md):
        if len(table) < 2:
            continue
        hdr = [_normalize_header(c) for c in table[0]]
        if not _is_epic_date_shift_table(hdr):
            continue
        idx_is = _date_shift_col(hdr, "initial start")
        idx_ie = _date_shift_col(hdr, "initial end")
        idx_ts = _date_shift_col(hdr, "target start")
        idx_te = _date_shift_col(hdr, "target end")
        if idx_is is None and idx_ie is None and idx_ts is None and idx_te is None:
            continue
        idx_epic = _gantt_find_col(hdr, ("epic id", "epic"))
        idx_title = _gantt_find_col(hdr, ("title",))
        idx_hz = _gantt_find_col(hdr, ("horizon", "window"))
        for row in table[2:]:
            if len(row) < len(hdr):
                row = row + [""] * (len(hdr) - len(row))

            def cell(i: int | None) -> str:
                if i is None or i >= len(row):
                    return ""
                return row[i] if i < len(row) else ""

            i_s = _parse_iso_date_str(cell(idx_is)) if idx_is is not None else None
            i_e = _parse_iso_date_str(cell(idx_ie)) if idx_ie is not None else None
            t_s = _parse_iso_date_str(cell(idx_ts)) if idx_ts is not None else None
            t_e = _parse_iso_date_str(cell(idx_te)) if idx_te is not None else None
            if not any((i_s, i_e, t_s, t_e)):
                continue
            hz_cell = cell(idx_hz) if idx_hz is not None else ""
            label = _gantt_row_label(row, idx_epic, idx_title, hz_cell)
            epic_id = ""
            if idx_epic is not None and idx_epic < len(row):
                cell_e = _strip_md_noise(row[idx_epic])
                m_e = _EPIC_ID_IN_CELL.search(cell_e)
                if m_e:
                    epic_id = m_e.group(1)
            rows_out.append(
                {
                    "label": label,
                    "epic_id": epic_id,
                    "initial_start": i_s,
                    "initial_end": i_e,
                    "target_start": t_s,
                    "target_end": t_e,
                }
            )

    return {
        "has_date_shift": bool(rows_out),
        "rows": rows_out,
    }


def _gantt_row_label(
    row: list[str],
    idx_epic: int | None,
    idx_title: int | None,
    hz_cell: str,
) -> str:
    label_parts: list[str] = []
    if idx_epic is not None and idx_epic < len(row):
        label_parts.append(_strip_md_noise(row[idx_epic])[:48])
    if idx_title is not None and idx_title < len(row):
        t = _strip_md_noise(row[idx_title])[:56]
        if t:
            label_parts.append(t)
    if len(label_parts) > 1:
        return " — ".join(label_parts)
    if label_parts:
        return label_parts[0]
    return _strip_md_noise(hz_cell)[:80] or "Epic"


def extract_gantt_model(md: str) -> dict[str, object]:
    """
    Ordinal Gantt data: milestone columns from milestone tables, bars from epic rows
    with Horizon cells like M1.1 or M1.1–M1.2.
    """
    milestones: list[str] = []
    mid_to_idx: dict[str, int] = {}
    bars: list[dict[str, object]] = []
    refs_for_fallback: list[str] = []

    tables = iter_gfm_tables(md)

    for table in tables:
        if len(table) < 2:
            continue
        hdr = [_normalize_header(c) for c in table[0]]
        if not hdr or not _is_milestone_schedule_table(hdr):
            continue
        idx_m = _gantt_find_col(hdr, ("milestone",))
        col = idx_m if idx_m is not None else 0
        for row in table[2:]:
            if len(row) < len(hdr):
                row = row + [""] * (len(hdr) - len(row))
            cell = row[col] if col < len(row) else ""
            mid = _parse_leading_milestone_id(cell)
            if mid and mid not in mid_to_idx:
                mid_to_idx[mid] = len(milestones)
                milestones.append(mid)

    for table in iter_gfm_tables(md):
        if len(table) < 2:
            continue
        hdr = [_normalize_header(c) for c in table[0]]
        if not _is_epic_horizon_table(hdr):
            continue
        idx_hz = _gantt_find_col(hdr, ("horizon", "window"))
        if idx_hz is None:
            continue
        for row in table[2:]:
            if len(row) < len(hdr):
                row = row + [""] * (len(hdr) - len(row))
            hz_cell = row[idx_hz] if idx_hz < len(row) else ""
            refs_for_fallback.extend(_all_milestone_refs_in_cell(hz_cell))

    if not milestones and refs_for_fallback:
        uniq = sorted(set(refs_for_fallback), key=_milestone_sort_key)
        milestones = uniq
        mid_to_idx = {m: i for i, m in enumerate(milestones)}

    for table in iter_gfm_tables(md):
        if len(table) < 2:
            continue
        hdr = [_normalize_header(c) for c in table[0]]
        if not _is_epic_horizon_table(hdr):
            continue
        idx_hz = _gantt_find_col(hdr, ("horizon", "window"))
        idx_epic = _gantt_find_col(hdr, ("epic id", "epic"))
        idx_title = _gantt_find_col(hdr, ("title",))
        idx_status = _gantt_find_col(hdr, ("status",))
        if idx_hz is None:
            continue
        for row in table[2:]:
            if len(row) < len(hdr):
                row = row + [""] * (len(hdr) - len(row))
            hz_cell = row[idx_hz] if idx_hz < len(row) else ""
            refs = _all_milestone_refs_in_cell(hz_cell)
            if not refs:
                continue
            label = _gantt_row_label(row, idx_epic, idx_title, hz_cell)
            st = ""
            if idx_status is not None and idx_status < len(row):
                st = _strip_md_noise(row[idx_status])[:48].lower()
            indices = [mid_to_idx[k] for k in refs if k in mid_to_idx]
            if not indices:
                continue
            i0, i1 = min(indices), max(indices)
            epic_id = ""
            if idx_epic is not None and idx_epic < len(row):
                cell_e = _strip_md_noise(row[idx_epic])
                m_e = _EPIC_ID_IN_CELL.search(cell_e)
                if m_e:
                    epic_id = m_e.group(1)
            bars.append(
                {
                    "label": label,
                    "start": i0,
                    "end": i1,
                    "status": st,
                    "epic_id": epic_id,
                }
            )

    has_gantt = bool(milestones and bars)
    return {
        "milestones": milestones,
        "bars": bars,
        "has_gantt": has_gantt,
    }


def _render_table_html(rows: list[list[str]]) -> str:
    if not rows:
        return ""
    thead = "<thead><tr>" + "".join(f"<th>{_esc(c)}</th>" for c in rows[0]) + "</tr></thead>"
    tbody_rows = []
    for r in rows[2:]:
        cells = r + [""] * (len(rows[0]) - len(r))
        cells = cells[: len(rows[0])]
        tbody_rows.append(
            "<tr>" + "".join(f"<td>{_esc(c)}</td>" for c in cells) + "</tr>"
        )
    tbody = "<tbody>" + "\n".join(tbody_rows) + "</tbody>"
    return (
        '<div class="table-responsive lenses-roadmap-table-wrap">'
        f'<table class="table table-sm table-bordered">{thead}{tbody}</table></div>'
    )


def _body_lines_to_html(body: str) -> str:
    lines = body.splitlines()
    parts: list[str] = []
    i = 0
    while i < len(lines):
        line = lines[i]
        hm = HEADING_RE.match(line)
        if hm:
            lev = len(hm.group(1))
            tit = hm.group(2).strip()
            tag = "h3" if lev <= 3 else "h4"
            parts.append(
                f'<{tag} class="h6 text-cyan mt-3 mb-2">{_esc(tit)}</{tag}>'
            )
            i += 1
            continue
        if "|" in line and line.strip().startswith("|"):
            block: list[str] = []
            while i < len(lines) and "|" in lines[i]:
                block.append(lines[i])
                i += 1
            parsed = _parse_pipe_table_rows(block)
            if parsed:
                parts.append(_render_table_html(parsed))
            else:
                parts.append(f"<p class='forge-support'>{_esc(chr(10).join(block))}</p>")
            continue
        if not line.strip():
            i += 1
            continue
        para: list[str] = []
        while i < len(lines) and lines[i].strip() and not (
            "|" in lines[i] and lines[i].strip().startswith("|")
        ):
            if HEADING_RE.match(lines[i]):
                break
            para.append(lines[i])
            i += 1
        if para:
            text = " ".join(para)
            parts.append(f'<p class="forge-support">{_esc(text)}</p>')
        continue
    return (
        "\n".join(parts)
        if parts
        else '<p class="forge-support text-muted"><span class="lenses-plan-empty-title">Empty section</span> — add body text in ROADMAP.md.</p>'
    )


def section_to_html(section: RoadmapSection) -> str:
    return (
        f'<div class="lenses-roadmap-section" data-section-id="{_esc(section.id)}">'
        f'<h2 class="h5 text-cyan mb-3">{_esc(section.title)}</h2>'
        f"{_body_lines_to_html(section.body)}"
        "</div>"
    )


def find_section(parsed: ParsedRoadmap, section_id: str) -> RoadmapSection | None:
    for s in parsed.sections:
        if s.id == section_id:
            return s
    return None
