"""Walk workspace HTML/Markdown sources and update the lenses search FTS index."""

from __future__ import annotations

import re
import sqlite3
from html.parser import HTMLParser
from pathlib import Path
from typing import Any, Callable
from urllib.parse import unquote, urljoin, urlparse

from lenses.scan import resolve_static_site_root
from lenses.search_db import (
    SOURCE_LENSES_DOCS,
    SOURCE_LOCAL_SITE,
    connect,
    delete_document,
    get_meta,
    search_db_path,
    search_max_bytes,
    set_indegree_counts,
    upsert_document,
)

_TITLE_RE = re.compile(r"<title[^>]*>([^<]{0,800})", re.I)
_H1_RE = re.compile(r"<h1[^>]*>(.*?)</h1>", re.I | re.DOTALL)

_MAX_DISCOVER_HTML = 8000
_MAX_DISCOVER_MD = 4000
_MAX_HEADINGS_CHARS = 8000
_FAKE_ORIGIN = "https://lenses.invalid"
_MD_LINK_RE = re.compile(r"\[[^\]]*]\(\s*([^)]+?)\s*\)")


def _strip_tags(s: str) -> str:
    t = re.sub(r"<[^>]+>", " ", s)
    t = re.sub(r"\s+", " ", t).strip()
    return t[:500]


class _HTMLTextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._chunks: list[str] = []
        self._skip = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        t = tag.lower()
        # Skip title so visible body text does not merge with <title> (breaks FTS tokens).
        if t in ("script", "style", "noscript", "template", "title"):
            self._skip += 1
        elif t in ("br", "p", "div", "li", "tr", "td", "th", "h1", "h2", "h3", "h4", "section", "article"):
            self._chunks.append(" ")

    def handle_endtag(self, tag: str) -> None:
        t = tag.lower()
        if t in ("script", "style", "noscript", "template", "title") and self._skip > 0:
            self._skip -= 1

    def handle_data(self, data: str) -> None:
        if self._skip == 0 and data:
            self._chunks.append(data)

    def text(self) -> str:
        raw = "".join(self._chunks)
        return " ".join(raw.split())


class _HeadingsExtractor(HTMLParser):
    """Plain text from ``h1``–``h6`` in document order (no nested heading edge cases)."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._in_heading = False
        self._cur: list[str] = []
        self._chunks: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        t = tag.lower()
        if t in ("h1", "h2", "h3", "h4", "h5", "h6"):
            self._in_heading = True
            self._cur = []

    def handle_endtag(self, tag: str) -> None:
        t = tag.lower()
        if t in ("h1", "h2", "h3", "h4", "h5", "h6"):
            chunk = " ".join("".join(self._cur).split())
            if chunk:
                self._chunks.append(chunk)
            self._in_heading = False
            self._cur = []

    def handle_data(self, data: str) -> None:
        if self._in_heading and data:
            self._cur.append(data)

    def headings_joined(self) -> str:
        s = " ".join(self._chunks)
        return s[:_MAX_HEADINGS_CHARS]


class _AnchorHrefCollector(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.hrefs: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() != "a":
            return
        d = {k.lower(): (v or "") for k, v in attrs}
        href = str(d.get("href", "")).strip()
        if href:
            self.hrefs.append(href)


def html_to_text_and_title(
    html_bytes: bytes, max_body_chars: int
) -> tuple[str, str, str]:
    """Return ``(body, title, headings)`` for FTS."""
    try:
        text = html_bytes.decode("utf-8", errors="ignore")
    except Exception:
        return "", "", ""
    head = text[: min(len(text), 96_000)]
    title_m = _TITLE_RE.search(head)
    h1_m = _H1_RE.search(head)
    title = ""
    if title_m:
        title = _strip_tags(title_m.group(1))
    if not title and h1_m:
        title = _strip_tags(h1_m.group(1))
    body_part = text
    if len(body_part) > max_body_chars:
        body_part = body_part[:max_body_chars]
    headings = ""
    try:
        hp = _HeadingsExtractor()
        hp.feed(body_part)
        hp.close()
        headings = hp.headings_joined()
    except Exception:
        headings = ""
    try:
        parser = _HTMLTextExtractor()
        parser.feed(body_part)
        parser.close()
        body = parser.text()
    except Exception:
        body = re.sub(r"<[^>]+>", " ", body_part)
        body = " ".join(body.split())
    if len(body) > max_body_chars:
        body = body[:max_body_chars]
    return body, title, headings


def md_to_text_and_title(raw: str, max_chars: int) -> tuple[str, str, str]:
    lines = raw.splitlines()
    title = ""
    heading_parts: list[str] = []
    for line in lines:
        s = line.strip()
        if re.match(r"^#{1,6}\s+", s):
            ht = re.sub(r"^#{1,6}\s+", "", s).strip()
            if ht:
                heading_parts.append(ht)
            if not title:
                title = ht
    headings = " ".join(heading_parts)[:_MAX_HEADINGS_CHARS]
    body = raw
    if len(body) > max_chars:
        body = body[:max_chars]
    return body, title, headings


def _path_key_local_site(site: str, rel_posix: str) -> str:
    return f"ls:local_site:{site}:{rel_posix}"


def _path_key_lenses_docs(rel_posix: str) -> str:
    return f"ls:lenses_docs:{rel_posix}"


def _url_local_site(site: str, rel_posix: str) -> str:
    rp = rel_posix.strip("/")
    if not rp:
        return f"/local-site/{site}/"
    return f"/local-site/{site}/{rp}"


def _url_docs(rel_posix: str) -> str:
    rp = rel_posix.strip("/")
    if not rp:
        return "/docs/"
    return f"/docs/{rp}"


def _resolve_internal_path(page_url: str, href: str) -> str | None:
    h = href.strip()
    if not h:
        return None
    low = h.lower()
    if low.startswith(("#", "javascript:", "mailto:", "tel:", "data:")):
        return None
    if h.startswith("//"):
        return None
    pu = page_url if page_url.startswith("/") else f"/{page_url}"
    base = f"{_FAKE_ORIGIN}{pu}"
    try:
        full = urljoin(base, h)
    except Exception:
        return None
    parsed = urlparse(full)
    if parsed.netloc and parsed.netloc != "lenses.invalid":
        return None
    path = unquote(parsed.path or "/")
    path = path.split("#", 1)[0].split("?", 1)[0]
    if not path.startswith("/"):
        path = "/" + path
    return path or None


def _path_key_from_canonical_path(path: str) -> str | None:
    p = path.rstrip("/") or "/"
    if p.startswith("/local-site/"):
        rest = p[len("/local-site/") :].strip("/")
        if not rest:
            return None
        parts = rest.split("/", 1)
        site = parts[0]
        rel = parts[1] if len(parts) > 1 else ""
        return _path_key_local_site(site, rel)
    if p == "/docs" or p.startswith("/docs"):
        rel = p[5:].lstrip("/") if len(p) > 5 else ""
        return _path_key_lenses_docs(rel)
    return None


def _collect_hrefs_from_html(html_bytes: bytes, max_read: int) -> list[str]:
    raw = html_bytes[:max_read].decode("utf-8", errors="ignore")
    try:
        p = _AnchorHrefCollector()
        p.feed(raw)
        p.close()
        return p.hrefs
    except Exception:
        return []


def _collect_hrefs_from_md(raw: str, max_read: int) -> list[str]:
    chunk = raw[:max_read]
    out: list[str] = []
    for m in _MD_LINK_RE.finditer(chunk):
        target = m.group(1).strip().strip('"').strip("'")
        if target and not target.lower().startswith(("#", "mailto:", "tel:", "javascript:")):
            out.append(target)
    return out


def _accumulate_indegree_for_workspace(
    wr: Path,
    docs_root: Path,
    ignore: set[str],
    conn: sqlite3.Connection,
    max_bytes: int,
) -> dict[str, int]:
    path_keys = {
        str(r[0])
        for r in conn.execute("SELECT path_key FROM search_fts").fetchall()
    }
    counts: dict[str, int] = {}

    def bump(target_pk: str) -> None:
        if target_pk in path_keys:
            counts[target_pk] = counts.get(target_pk, 0) + 1

    if wr.is_dir():
        for p in sorted(wr.iterdir(), key=lambda x: x.name.lower()):
            if not p.is_dir() or p.name.startswith("."):
                continue
            if p.name in ignore:
                continue
            site = p.name
            base = resolve_static_site_root(p)
            if base is None:
                continue
            html_files: list[Path] = []
            for ext in ("*.html", "*.htm"):
                for f in base.rglob(ext):
                    if f.is_file():
                        html_files.append(f)
                    if len(html_files) >= _MAX_DISCOVER_HTML:
                        break
                if len(html_files) >= _MAX_DISCOVER_HTML:
                    break
            md_files: list[Path] = []
            for f in base.rglob("*.md"):
                if f.is_file():
                    md_files.append(f)
                if len(md_files) >= _MAX_DISCOVER_MD:
                    break
            for fpath in sorted(html_files + md_files, key=lambda x: x.as_posix().lower()):
                try:
                    rel = fpath.relative_to(base).as_posix()
                except ValueError:
                    continue
                page_url = _url_local_site(site, rel)
                st = fpath.stat()
                if int(st.st_size) > max_bytes:
                    continue
                if fpath.suffix.lower() in (".html", ".htm"):
                    raw_b = fpath.read_bytes()
                    if len(raw_b) > max_bytes:
                        raw_b = raw_b[:max_bytes]
                    for href in _collect_hrefs_from_html(raw_b, len(raw_b)):
                        cpath = _resolve_internal_path(page_url, href)
                        if cpath is None:
                            continue
                        tpk = _path_key_from_canonical_path(cpath)
                        if tpk:
                            bump(tpk)
                else:
                    raw_t = fpath.read_text(encoding="utf-8", errors="ignore")
                    if len(raw_t.encode("utf-8")) > max_bytes:
                        raw_t = raw_t.encode("utf-8")[:max_bytes].decode(
                            "utf-8", errors="ignore"
                        )
                    for href in _collect_hrefs_from_md(raw_t, len(raw_t)):
                        cpath = _resolve_internal_path(page_url, href)
                        if cpath is None:
                            continue
                        tpk = _path_key_from_canonical_path(cpath)
                        if tpk:
                            bump(tpk)

    if docs_root.is_dir():
        html_files: list[Path] = []
        for ext in ("*.html", "*.htm"):
            for f in docs_root.rglob(ext):
                if f.is_file():
                    html_files.append(f)
                if len(html_files) >= _MAX_DISCOVER_HTML:
                    break
            if len(html_files) >= _MAX_DISCOVER_HTML:
                break
        md_files: list[Path] = []
        for f in docs_root.rglob("*.md"):
            if f.is_file():
                md_files.append(f)
            if len(md_files) >= _MAX_DISCOVER_MD:
                break
        for fpath in sorted(html_files + md_files, key=lambda x: x.as_posix().lower()):
            try:
                rel = fpath.relative_to(docs_root).as_posix()
            except ValueError:
                continue
            page_url = _url_docs(rel)
            st = fpath.stat()
            if int(st.st_size) > max_bytes:
                continue
            if fpath.suffix.lower() in (".html", ".htm"):
                raw_b = fpath.read_bytes()
                if len(raw_b) > max_bytes:
                    raw_b = raw_b[:max_bytes]
                for href in _collect_hrefs_from_html(raw_b, len(raw_b)):
                    cpath = _resolve_internal_path(page_url, href)
                    if cpath is None:
                        continue
                    tpk = _path_key_from_canonical_path(cpath)
                    if tpk:
                        bump(tpk)
            else:
                raw_t = fpath.read_text(encoding="utf-8", errors="ignore")
                if len(raw_t.encode("utf-8")) > max_bytes:
                    raw_t = raw_t.encode("utf-8")[:max_bytes].decode(
                        "utf-8", errors="ignore"
                    )
                for href in _collect_hrefs_from_md(raw_t, len(raw_t)):
                    cpath = _resolve_internal_path(page_url, href)
                    if cpath is None:
                        continue
                    tpk = _path_key_from_canonical_path(cpath)
                    if tpk:
                        bump(tpk)

    return counts


def reindex_workspace(
    workspace_root: Path,
    lenses_repo_root: Path,
    registry: dict[str, Any],
    *,
    progress: Callable[[str, int], None] | None = None,
) -> dict[str, Any]:
    """
    Index HTML/MD under each workspace child's static output directory and ``lenses-docs/``.

    Static root per child comes from :func:`resolve_static_site_root` (``firebase.json``
    ``hosting.public`` when present, else ``website/``, ``public/``, or ``dist/``). No Firebase
    runtime or account is required.

    Removes DB rows for sources ``local_site`` / ``lenses_docs`` that no longer exist on disk.
    """
    max_bytes = search_max_bytes()
    max_chars = max_bytes
    wr = workspace_root.resolve()
    docs_root = (lenses_repo_root / "lenses-docs").resolve()
    conn = connect(wr)
    indexed = 0
    skipped = 0
    current_local: set[str] = set()
    current_docs: set[str] = set()

    try:
        ignore = set(registry.get("ignore_paths") or [])

        if wr.is_dir():
            for p in sorted(wr.iterdir(), key=lambda x: x.name.lower()):
                if not p.is_dir() or p.name.startswith("."):
                    continue
                if p.name in ignore:
                    continue
                site = p.name
                base = resolve_static_site_root(p)
                if base is None:
                    continue

                html_files: list[Path] = []
                for ext in ("*.html", "*.htm"):
                    for f in base.rglob(ext):
                        if f.is_file():
                            html_files.append(f)
                        if len(html_files) >= _MAX_DISCOVER_HTML:
                            break
                    if len(html_files) >= _MAX_DISCOVER_HTML:
                        break
                md_files: list[Path] = []
                for f in base.rglob("*.md"):
                    if f.is_file():
                        md_files.append(f)
                    if len(md_files) >= _MAX_DISCOVER_MD:
                        break

                for fpath in sorted(html_files + md_files, key=lambda x: x.as_posix().lower()):
                    try:
                        rel = fpath.relative_to(base).as_posix()
                    except ValueError:
                        continue
                    pk = _path_key_local_site(site, rel)
                    current_local.add(pk)
                    st = fpath.stat()
                    mtime_ns = int(getattr(st, "st_mtime_ns", int(st.st_mtime * 1e9)))
                    size_b = int(st.st_size)
                    meta = get_meta(conn, pk)
                    if meta == (mtime_ns, size_b):
                        skipped += 1
                        continue
                    if size_b > max_bytes:
                        continue
                    if fpath.suffix.lower() in (".html", ".htm"):
                        raw = fpath.read_bytes()
                        if len(raw) > max_bytes:
                            raw = raw[:max_bytes]
                        body, title, headings = html_to_text_and_title(raw, max_chars)
                    else:
                        raw_t = fpath.read_text(encoding="utf-8", errors="ignore")
                        if len(raw_t.encode("utf-8")) > max_bytes:
                            raw_t = raw_t.encode("utf-8")[:max_bytes].decode(
                                "utf-8", errors="ignore"
                            )
                        body, title, headings = md_to_text_and_title(raw_t, max_chars)
                    url = _url_local_site(site, rel)
                    upsert_document(
                        conn,
                        path_key=pk,
                        url=url,
                        title=title,
                        headings=headings,
                        body=body,
                        source=SOURCE_LOCAL_SITE,
                        mtime_ns=mtime_ns,
                        size_bytes=size_b,
                    )
                    indexed += 1
                    if progress:
                        progress(pk, indexed)

        if docs_root.is_dir():
            html_files: list[Path] = []
            for ext in ("*.html", "*.htm"):
                for f in docs_root.rglob(ext):
                    if f.is_file():
                        html_files.append(f)
                    if len(html_files) >= _MAX_DISCOVER_HTML:
                        break
                if len(html_files) >= _MAX_DISCOVER_HTML:
                    break
            md_files: list[Path] = []
            for f in docs_root.rglob("*.md"):
                if f.is_file():
                    md_files.append(f)
                if len(md_files) >= _MAX_DISCOVER_MD:
                    break

            for fpath in sorted(html_files + md_files, key=lambda x: x.as_posix().lower()):
                try:
                    rel = fpath.relative_to(docs_root).as_posix()
                except ValueError:
                    continue
                pk = _path_key_lenses_docs(rel)
                current_docs.add(pk)
                st = fpath.stat()
                mtime_ns = int(getattr(st, "st_mtime_ns", int(st.st_mtime * 1e9)))
                size_b = int(st.st_size)
                meta = get_meta(conn, pk)
                if meta == (mtime_ns, size_b):
                    skipped += 1
                    continue
                if size_b > max_bytes:
                    continue
                if fpath.suffix.lower() in (".html", ".htm"):
                    raw = fpath.read_bytes()
                    if len(raw) > max_bytes:
                        raw = raw[:max_bytes]
                    body, title, headings = html_to_text_and_title(raw, max_chars)
                else:
                    raw_t = fpath.read_text(encoding="utf-8", errors="ignore")
                    if len(raw_t.encode("utf-8")) > max_bytes:
                        raw_t = raw_t.encode("utf-8")[:max_bytes].decode(
                            "utf-8", errors="ignore"
                        )
                    body, title, headings = md_to_text_and_title(raw_t, max_chars)
                upsert_document(
                    conn,
                    path_key=pk,
                    url=_url_docs(rel),
                    title=title,
                    headings=headings,
                    body=body,
                    source=SOURCE_LENSES_DOCS,
                    mtime_ns=mtime_ns,
                    size_bytes=size_b,
                )
                indexed += 1
                if progress:
                    progress(pk, indexed)

        # Orphan removal: paths removed from disk
        prev_local = [
            str(r[0])
            for r in conn.execute(
                "SELECT path_key FROM search_meta WHERE source = ?",
                (SOURCE_LOCAL_SITE,),
            ).fetchall()
        ]
        for k in prev_local:
            if k not in current_local:
                delete_document(conn, k)

        prev_docs = [
            str(r[0])
            for r in conn.execute(
                "SELECT path_key FROM search_meta WHERE source = ?",
                (SOURCE_LENSES_DOCS,),
            ).fetchall()
        ]
        for k in prev_docs:
            if k not in current_docs:
                delete_document(conn, k)

        indeg = _accumulate_indegree_for_workspace(
            wr, docs_root, ignore, conn, max_bytes
        )
        set_indegree_counts(conn, indeg)

        conn.commit()
    finally:
        conn.close()

    return {
        "ok": True,
        "indexed": indexed,
        "skipped": skipped,
        "db_path": str(search_db_path(wr)),
    }
