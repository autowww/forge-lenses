"""Hydrate sticker boards from product workshop kickoff Markdown."""

from __future__ import annotations

import re
import secrets
import string
from pathlib import Path
from typing import Any

from lenses.sticker_board import MAX_BODY_LEN, MAX_STICKERS, MAX_TITLE_LEN

_SECTION_RE = re.compile(r"^##\s+(.+)$", re.MULTILINE)
_SUBSECTION_RE = re.compile(r"^###\s+(.+)$", re.MULTILINE)
_JOURNEY_ARROW_RE = re.compile(r"→|->")
_HANDLED_SECTIONS = frozenset(
    {
        "workshop validation board",
        "feature map for validation",
        "main product journey to validate",
        "main product journey",
        "suggested 90-minute workshop agenda",
        "suggested 90 minute workshop agenda",
    }
)


def _sticker_uid() -> str:
    alphabet = string.ascii_lowercase + string.digits
    return "s-" + "".join(secrets.choice(alphabet) for _ in range(10))


def _norm_heading(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").strip().lower())


def _parse_simple_frontmatter(md: str) -> tuple[dict[str, Any], str]:
    """Return (lenses_workshop dict, body without frontmatter)."""
    if not md.startswith("---"):
        return {}, md
    end = md.find("\n---", 3)
    if end < 0:
        return {}, md
    block = md[3:end].strip()
    body = md[end + 4 :].lstrip("\n")
    meta: dict[str, Any] = {}
    in_workshop = False
    workshop: dict[str, Any] = {}
    for line in block.splitlines():
        stripped = line.strip()
        if stripped == "lenses_workshop:":
            in_workshop = True
            continue
        if in_workshop:
            if stripped and not stripped[0].isspace() and ":" in stripped and not line.startswith(" "):
                in_workshop = False
            elif ":" in stripped:
                key, _, val = stripped.partition(":")
                workshop[key.strip()] = val.strip().strip('"').strip("'")
                continue
        if ":" in stripped and not in_workshop:
            key, _, val = stripped.partition(":")
            meta[key.strip()] = val.strip().strip('"').strip("'")
    if workshop:
        meta["lenses_workshop"] = workshop
    return meta, body


def _split_sections(body: str) -> list[tuple[str, str]]:
    """Split markdown body into (heading, content) for each ## section."""
    matches = list(_SECTION_RE.finditer(body))
    if not matches:
        return [("", body)]
    out: list[tuple[str, str]] = []
    if matches[0].start() > 0:
        pre = body[: matches[0].start()].strip()
        if pre:
            out.append(("", pre))
    for i, m in enumerate(matches):
        title = m.group(1).strip()
        start = m.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(body)
        out.append((title, body[start:end].strip()))
    return out


def _parse_markdown_table(content: str) -> tuple[list[str], list[list[str]]]:
    """Parse a pipe table; return (headers, data rows). Skips separator rows."""
    lines = [ln.strip() for ln in content.splitlines() if "|" in ln]
    if len(lines) < 2:
        return [], []
    rows: list[list[str]] = []
    for ln in lines:
        cells = [c.strip() for c in ln.strip("|").split("|")]
        if not cells:
            continue
        if all(re.match(r"^:?-+:?$", c.replace(" ", "")) for c in cells if c):
            continue
        rows.append(cells)
    if not rows:
        return [], []
    headers = rows[0]
    data = rows[1:]
    return headers, data


def _journey_stages_from_content(content: str) -> list[tuple[str, str]]:
    """Extract journey stages from fenced text or Stage table."""
    stages: list[tuple[str, str]] = []
    for m in re.finditer(r"```(?:text)?\s*\n([^`]+)```", content, re.DOTALL):
        block = m.group(1).strip()
        for part in _JOURNEY_ARROW_RE.split(block):
            stage = part.strip()
            if stage and len(stage) < 120:
                stages.append((stage, ""))
        if stages:
            return stages
    headers, data = _parse_markdown_table(content)
    if headers and _norm_heading(headers[0]) in ("stage", "step"):
        q_idx = 1
        if len(headers) > 1 and "question" in _norm_heading(headers[1]):
            q_idx = 1
        for row in data:
            if not row:
                continue
            title = row[0].strip().strip("*")
            body = row[q_idx].strip() if len(row) > q_idx else ""
            if title:
                stages.append((title, body))
        if stages:
            return stages
    for part in _JOURNEY_ARROW_RE.split(content):
        stage = part.strip()
        if stage and "→" not in stage and "->" not in stage and len(stage) < 80:
            if re.match(r"^[A-Za-z][\w\s/&-]+$", stage):
                stages.append((stage, ""))
    return stages


def _split_agenda_subsections(content: str) -> list[tuple[str, str]]:
    matches = list(_SUBSECTION_RE.finditer(content))
    if not matches:
        return []
    out: list[tuple[str, str]] = []
    for i, m in enumerate(matches):
        title = m.group(1).strip()
        start = m.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(content)
        out.append((title, content[start:end].strip()))
    return out


def _extract_agenda_body(sub_content: str) -> str:
    parts: list[str] = []
    for label in ("Goal:", "Prompt:", "Decision to capture:", "Decision to capture"):
        m = re.search(rf"{re.escape(label)}\s*\n?", sub_content, re.IGNORECASE)
        if m:
            start = m.end()
            nxt = re.search(
                r"\n(?:Goal:|Prompt:|Decision to capture:|-\s)",
                sub_content[start:],
                re.IGNORECASE,
            )
            chunk = sub_content[start : start + nxt.start()] if nxt else sub_content[start:]
            parts.append(f"**{label.rstrip(':')}**\n{chunk.strip()}")
    if parts:
        return "\n\n".join(parts)[:MAX_BODY_LEN]
    return sub_content[:MAX_BODY_LEN]


def parse_workshop_kickoff_markdown(md: str) -> dict[str, Any]:
    """
    Parse workshop kickoff Markdown into sticker seeds and metadata.

    Returns dict with keys: frontmatter, sections, warnings, stickers (seed dicts).
    """
    front, body = _parse_simple_frontmatter(md)
    sections_parsed: list[str] = []
    warnings: list[str] = []
    seeds: list[dict[str, Any]] = []

    for heading, content in _split_sections(body):
        hnorm = _norm_heading(heading)
        if not heading:
            continue

        if "workshop validation board" in hnorm:
            headers, rows = _parse_markdown_table(content)
            if not rows:
                warnings.append("validation_board_empty")
                continue
            dec_col = 0
            opt_col = 1
            for i, h in enumerate(headers):
                hn = _norm_heading(h)
                if hn == "decision" or (hn.startswith("decision") and "team" not in hn):
                    dec_col = i
                elif "option" in hn:
                    opt_col = i
            for row in rows:
                if len(row) <= dec_col:
                    continue
                title = row[dec_col].strip().strip("*")[:MAX_TITLE_LEN]
                if not title or title.lower() == "decision":
                    continue
                opts = row[opt_col].strip() if len(row) > opt_col else ""
                body_text = f"**Options:** {opts}\n\n**Team decision:**\n"[:MAX_BODY_LEN]
                seeds.append(
                    {
                        "title": title,
                        "body": body_text,
                        "column_id": "discuss",
                        "source_kind": "validation_decision",
                    }
                )
            sections_parsed.append("validation_board")

        elif "feature map" in hnorm and "validation" in hnorm:
            headers, rows = _parse_markdown_table(content)
            feat_col = 0
            sig_col = 1
            q_col = 3
            for i, h in enumerate(headers):
                hn = _norm_heading(h)
                if "feature" in hn:
                    feat_col = i
                elif "archive" in hn or "signal" in hn:
                    sig_col = i
                elif "question" in hn or "validation" in hn:
                    q_col = i
            for row in rows:
                if len(row) <= feat_col:
                    continue
                title = row[feat_col].strip().strip("*")[:MAX_TITLE_LEN]
                if not title or title.lower() == "feature area":
                    continue
                parts = []
                if len(row) > sig_col:
                    parts.append(f"**Signal:** {row[sig_col].strip()}")
                if len(row) > q_col:
                    parts.append(f"**Question:** {row[q_col].strip()}")
                seeds.append(
                    {
                        "title": title,
                        "body": "\n\n".join(parts)[:MAX_BODY_LEN],
                        "column_id": "discuss",
                        "source_kind": "feature_area",
                    }
                )
            sections_parsed.append("feature_map")

        elif "agenda" in hnorm and ("90" in hnorm or "minute" in hnorm or "workshop" in hnorm):
            for sub_title, sub_content in _split_agenda_subsections(content):
                title = sub_title[:MAX_TITLE_LEN]
                body_text = _extract_agenda_body(sub_content)
                seeds.append(
                    {
                        "title": title,
                        "body": body_text,
                        "column_id": "parking",
                        "source_kind": "agenda_block",
                    }
                )
            sections_parsed.append("agenda")

        elif ("journey" in hnorm and "validate" in hnorm) or hnorm == "main product journey":
            stages = _journey_stages_from_content(content)
            for title, body_text in stages:
                seeds.append(
                    {
                        "title": title[:MAX_TITLE_LEN],
                        "body": body_text[:MAX_BODY_LEN],
                        "column_id": "discuss",
                        "source_kind": "journey_stage",
                    }
                )
            if stages:
                sections_parsed.append("journey")

        elif hnorm not in _HANDLED_SECTIONS:
            anchor_body = content[:2000].strip()
            if anchor_body:
                seeds.append(
                    {
                        "title": heading[:MAX_TITLE_LEN],
                        "body": anchor_body[:MAX_BODY_LEN],
                        "column_id": "parking",
                        "source_kind": "section_anchor",
                    }
                )
                sections_parsed.append(f"anchor:{hnorm[:40]}")

    return {
        "frontmatter": front,
        "sections": sections_parsed,
        "warnings": warnings,
        "stickers": seeds,
    }


def _safe_workspace_md_path(workspace_root: Path, rel: str) -> Path | None:
    rel_norm = rel.replace("\\", "/").strip().strip("/")
    if not rel_norm or ".." in rel_norm.split("/"):
        return None
    candidate = (workspace_root / rel_norm).resolve()
    try:
        candidate.relative_to(workspace_root.resolve())
    except ValueError:
        return None
    if not candidate.is_file() or candidate.suffix.lower() != ".md":
        return None
    return candidate


def hydrate_board_from_workshop_md(
    workspace_root: Path,
    board_state: dict[str, Any],
    *,
    workshop_md_path: str = "",
    workshop_md_text: str = "",
) -> tuple[dict[str, Any], dict[str, Any]]:
    """
    Add stickers from workshop kickoff Markdown.

    Returns (board_state, meta) with prefill_ok, prefill_message, stickers_added, sections.
    """
    meta: dict[str, Any] = {
        "prefill_ok": False,
        "prefill_message": "",
        "stickers_added": 0,
        "sections": [],
        "warnings": [],
    }
    text = (workshop_md_text or "").strip()
    if not text and workshop_md_path:
        resolved = _safe_workspace_md_path(workspace_root, workshop_md_path)
        if resolved is None:
            meta["prefill_message"] = "workshop_md_missing"
            return board_state, meta
        try:
            text = resolved.read_text(encoding="utf-8")
        except OSError:
            meta["prefill_message"] = "workshop_md_read_error"
            return board_state, meta
    if not text:
        meta["prefill_message"] = "workshop_md_empty"
        return board_state, meta

    try:
        parsed = parse_workshop_kickoff_markdown(text)
    except Exception:
        meta["prefill_message"] = "workshop_md_parse_error"
        return board_state, meta

    seeds = parsed.get("stickers") or []
    if not seeds:
        meta["prefill_message"] = "workshop_md_no_stickers"
        meta["warnings"] = list(parsed.get("warnings") or [])
        return board_state, meta

    col_ids = {c["id"] for c in board_state.get("columns") or [] if isinstance(c, dict)}
    stickers: list[dict[str, Any]] = list(board_state.get("stickers") or [])
    order_by_col: dict[str, int] = {}

    for seed in seeds:
        if len(stickers) >= MAX_STICKERS:
            meta.setdefault("warnings", []).append("max_stickers_reached")
            break
        if not isinstance(seed, dict):
            continue
        cid = str(seed.get("column_id") or "discuss")
        if cid not in col_ids:
            cid = "discuss" if "discuss" in col_ids else (next(iter(col_ids), None) or "parking")
        if cid not in order_by_col:
            order_by_col[cid] = 0
        st: dict[str, Any] = {
            "id": _sticker_uid(),
            "title": str(seed.get("title", ""))[:MAX_TITLE_LEN],
            "body": str(seed.get("body", ""))[:MAX_BODY_LEN],
            "column_id": cid,
            "order": order_by_col[cid],
            "x": 0.0,
            "y": 0.0,
        }
        sk = seed.get("source_kind")
        if sk:
            st["source_kind"] = str(sk)
        order_by_col[cid] += 1
        stickers.append(st)

    lw = (parsed.get("frontmatter") or {}).get("lenses_workshop") or {}
    if isinstance(lw, dict):
        phase = str(lw.get("default_phase", "")).strip().lower()
        if phase in ("discover", "score", "prioritize", "capture"):
            board_state["workshop_phase"] = phase

    board_state["stickers"] = stickers
    board_state["prefill_applied"] = True
    meta["prefill_ok"] = True
    meta["prefill_message"] = "ok"
    meta["stickers_added"] = len(seeds)
    meta["sections"] = list(parsed.get("sections") or [])
    meta["warnings"] = list(parsed.get("warnings") or [])
    return board_state, meta
