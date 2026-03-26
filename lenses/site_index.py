"""Lightweight HTML page index for local site preview (title / h1 extraction)."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

_TITLE_RE = re.compile(r"<title[^>]*>([^<]{0,400})", re.I)
_H1_RE = re.compile(r"<h1[^>]*>(.*?)</h1>", re.I | re.DOTALL)


def _strip_tags(s: str) -> str:
    t = re.sub(r"<[^>]+>", " ", s)
    t = re.sub(r"\s+", " ", t).strip()
    return t[:240]


def _index_html_file(path: Path, public_root: Path) -> dict[str, Any] | None:
    rel = path.relative_to(public_root).as_posix()
    try:
        chunk = path.read_bytes()[:48_000]
        text = chunk.decode("utf-8", errors="ignore")
    except OSError:
        return None
    title_m = _TITLE_RE.search(text)
    h1_m = _H1_RE.search(text)
    title = _strip_tags(title_m.group(1)) if title_m else ""
    h1 = _strip_tags(h1_m.group(1)) if h1_m else ""
    label = title or h1 or rel
    return {"path": rel, "title": title, "h1": h1, "label": label}


def build_html_page_index(
    public_root: Path,
    *,
    max_indexed: int = 200,
    max_discovered: int = 5000,
) -> dict[str, Any]:
    """Return index entries plus counts for one Firebase public directory."""
    if not public_root.is_dir():
        return {
            "pages": [],
            "html_total": 0,
            "html_indexed": 0,
            "index_html_mtime": None,
        }
    html_files: list[Path] = []
    for p in public_root.rglob("*.html"):
        html_files.append(p)
        if len(html_files) >= max_discovered:
            break
    html_files.sort(key=lambda x: x.as_posix().lower())
    total = len(html_files)
    pages: list[dict[str, Any]] = []
    for p in html_files[:max_indexed]:
        row = _index_html_file(p, public_root)
        if row:
            pages.append(row)
    idx = public_root / "index.html"
    mtime = None
    if idx.is_file():
        try:
            mtime = idx.stat().st_mtime
        except OSError:
            mtime = None
    return {
        "pages": pages,
        "html_total": total,
        "html_indexed": len(pages),
        "index_html_mtime": mtime,
    }
