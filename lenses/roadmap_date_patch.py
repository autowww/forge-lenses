"""Apply epic date cell updates to ROADMAP.md (Initial/Target columns)."""

from __future__ import annotations

import re
from typing import Any

ISO_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_EPIC_ID = re.compile(r"\b(M\d+E\d+)\b")


def _norm_header(cell: str) -> str:
    return re.sub(r"\s+", " ", cell.strip().lower())


def apply_epic_date_updates(md: str, updates: list[dict[str, Any]]) -> tuple[str, str | None]:
    """
    Patch the first GFM epic table that has Initial/Target date columns.

    Each update must include ``epic_id`` (e.g. ``M1E1``). Optional keys:
    ``initial_start``, ``initial_end``, ``target_start``, ``target_end`` —
    ISO ``YYYY-MM-DD`` or empty string to clear.
    """
    if not updates:
        return md, None
    up_by_eid: dict[str, dict[str, Any]] = {}
    for u in updates:
        eid = str(u.get("epic_id") or "").strip()
        if eid:
            up_by_eid[eid] = u
    if not up_by_eid:
        return md, "missing_epic_id"

    lines = md.splitlines(keepends=True)
    i = 0
    while i < len(lines):
        line = lines[i]
        if "|" not in line or not line.strip().startswith("|"):
            i += 1
            continue
        block_start = i
        block: list[str] = []
        j = i
        while j < len(lines) and "|" in lines[j]:
            block.append(lines[j])
            j += 1
        if len(block) < 3:
            i = j
            continue
        hdr_cells = [c.strip() for c in block[0].strip().strip("|").split("|")]
        hdr = [_norm_header(c) for c in hdr_cells]
        joined = " ".join(hdr)
        if "epic" not in joined:
            i = j
            continue
        needles = ("initial start", "initial end", "target start", "target end")
        if not all(any(nd in h for h in hdr) for nd in needles):
            i = j
            continue

        def col_idx(sub: str) -> int | None:
            for idx, h in enumerate(hdr):
                if sub in h:
                    return idx
            return None

        idx_epic = col_idx("epic id")
        if idx_epic is None:
            idx_epic = col_idx("epic")
        ix: dict[str, int | None] = {
            "initial_start": col_idx("initial start"),
            "initial_end": col_idx("initial end"),
            "target_start": col_idx("target start"),
            "target_end": col_idx("target end"),
        }
        if idx_epic is None or any(ix[k] is None for k in ix):
            i = j
            continue

        ncols = len(hdr_cells)
        new_block = [block[0], block[1]]
        changed = False
        for row_line in block[2:]:
            raw = row_line.rstrip("\n")
            if not raw.strip().startswith("|"):
                new_block.append(row_line)
                continue
            cells = [c.strip() for c in raw.strip().strip("|").split("|")]
            while len(cells) < ncols:
                cells.append("")
            cells = cells[:ncols]
            epic_cell = cells[idx_epic] if idx_epic < len(cells) else ""
            clean = re.sub(r"\*+", "", epic_cell)
            m = _EPIC_ID.search(clean)
            eid = m.group(1) if m else ""
            if eid not in up_by_eid:
                new_block.append(row_line)
                continue
            u = up_by_eid[eid]
            for key in ("initial_start", "initial_end", "target_start", "target_end"):
                if key not in u:
                    continue
                val = str(u.get(key) or "").strip()
                if val and not ISO_DATE.match(val):
                    return md, f"invalid_date:{key}"
                col = ix[key]
                assert col is not None
                cells[col] = val
            new_line = "| " + " | ".join(cells) + " |\n"
            new_block.append(new_line)
            changed = True

        if changed:
            return "".join(lines[:block_start] + new_block + lines[j:]), None
        i = j
    return md, "date_table_not_found"
