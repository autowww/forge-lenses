"""SQLite FTS5 index for lenses local search (data under workspace ``.lenses-local/``)."""

from __future__ import annotations

import math
import os
import re
import sqlite3
from pathlib import Path
from typing import Any

# Sources stored in the FTS table (UNINDEXED column ``source``).
SOURCE_LOCAL_SITE = "local_site"
SOURCE_LENSES_DOCS = "lenses_docs"
SOURCE_INGESTED = "ingested"

_SCHEMA_VERSION = 2
_DEFAULT_MAX_MB = 8.0

# BM25 weights: title, headings, body (lower weight = more influence on rank magnitude).
_BM25_W_TITLE = 5.0
_BM25_W_HEADINGS = 3.0
_BM25_W_BODY = 1.0
# Subtract from bm25 so higher indegree sorts earlier (bm25 ASC = better).
_REF_COUNT_SCALE = 0.35


def search_max_bytes() -> int:
    raw = os.environ.get("LENSES_SEARCH_MAX_MB", "").strip()
    try:
        mb = float(raw) if raw else _DEFAULT_MAX_MB
    except ValueError:
        mb = _DEFAULT_MAX_MB
    if mb <= 0:
        mb = _DEFAULT_MAX_MB
    return int(mb * 1024 * 1024)


def search_db_path(workspace_root: Path) -> Path:
    root = workspace_root.resolve()
    local = root / ".lenses-local"
    return local / "lenses-search.sqlite"


def _migrate_schema_if_needed(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS _lenses_search_schema (
          id INTEGER PRIMARY KEY CHECK (id = 1),
          version INTEGER NOT NULL
        )
        """
    )
    row = conn.execute(
        "SELECT version FROM _lenses_search_schema WHERE id = 1"
    ).fetchone()
    ver = int(row[0]) if row else 0
    if ver >= _SCHEMA_VERSION:
        return
    conn.executescript(
        """
        DROP TABLE IF EXISTS search_fts;
        DROP TABLE IF EXISTS search_indegree;
        DROP TABLE IF EXISTS search_meta;
        """
    )
    conn.execute(
        """
        INSERT OR REPLACE INTO _lenses_search_schema(id, version)
        VALUES (1, ?)
        """,
        (_SCHEMA_VERSION,),
    )
    conn.commit()


def connect(workspace_root: Path) -> sqlite3.Connection:
    db_path = search_db_path(workspace_root)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path), timeout=30.0)
    conn.row_factory = sqlite3.Row
    _migrate_schema_if_needed(conn)
    init_schema(conn)
    return conn


def init_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS search_meta (
          path_key TEXT PRIMARY KEY,
          mtime_ns INTEGER NOT NULL,
          size_bytes INTEGER NOT NULL,
          source TEXT NOT NULL
        );

        CREATE VIRTUAL TABLE IF NOT EXISTS search_fts USING fts5(
          path_key UNINDEXED,
          url UNINDEXED,
          title,
          headings,
          body,
          source UNINDEXED,
          tokenize = 'unicode61'
        );

        CREATE TABLE IF NOT EXISTS search_indegree (
          path_key TEXT PRIMARY KEY,
          ref_count INTEGER NOT NULL
        );
        """
    )
    conn.commit()


def _fts_escape_term(term: str) -> str:
    t = term.strip()
    if not t:
        return ""
    return '"' + t.replace('"', '""') + '"'


def build_fts_match_query(user_query: str) -> str | None:
    """Turn free text into a safe FTS5 AND query (token alphanumerics)."""
    tokens = re.findall(r"[\w\u0080-\uFFFF]{2,}", user_query, flags=re.UNICODE)
    if not tokens:
        tokens = re.findall(r"\S+", user_query.strip())
    if not tokens:
        return None
    parts = [_fts_escape_term(t) for t in tokens if t.strip()]
    if not parts:
        return None
    return " AND ".join(parts)


def delete_document(conn: sqlite3.Connection, path_key: str) -> None:
    conn.execute("DELETE FROM search_fts WHERE path_key = ?", (path_key,))
    conn.execute("DELETE FROM search_meta WHERE path_key = ?", (path_key,))
    conn.execute("DELETE FROM search_indegree WHERE path_key = ?", (path_key,))


def upsert_document(
    conn: sqlite3.Connection,
    *,
    path_key: str,
    url: str,
    title: str,
    headings: str,
    body: str,
    source: str,
    mtime_ns: int,
    size_bytes: int,
) -> None:
    delete_document(conn, path_key)
    conn.execute(
        """
        INSERT INTO search_fts(path_key, url, title, headings, body, source)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (path_key, url, title, headings, body, source),
    )
    conn.execute(
        """
        INSERT OR REPLACE INTO search_meta(path_key, mtime_ns, size_bytes, source)
        VALUES (?, ?, ?, ?)
        """,
        (path_key, mtime_ns, size_bytes, source),
    )
    conn.execute(
        "INSERT OR IGNORE INTO search_indegree(path_key, ref_count) VALUES (?, 0)",
        (path_key,),
    )


def set_indegree_counts(conn: sqlite3.Connection, counts: dict[str, int]) -> None:
    """Replace all indegree rows (call after full link scan)."""
    conn.execute("DELETE FROM search_indegree")
    for pk, n in counts.items():
        if n > 0:
            conn.execute(
                "INSERT INTO search_indegree(path_key, ref_count) VALUES (?, ?)",
                (pk, n),
            )
    # Ensure every indexed doc has a row (0 refs)
    conn.execute(
        """
        INSERT OR IGNORE INTO search_indegree(path_key, ref_count)
        SELECT path_key, 0 FROM search_fts
        """
    )


def get_meta(conn: sqlite3.Connection, path_key: str) -> tuple[int, int] | None:
    row = conn.execute(
        "SELECT mtime_ns, size_bytes FROM search_meta WHERE path_key = ?",
        (path_key,),
    ).fetchone()
    if row is None:
        return None
    return int(row[0]), int(row[1])


def search(
    conn: sqlite3.Connection,
    user_query: str,
    *,
    limit: int = 25,
    offset: int = 0,
    scope_site: str = "",
) -> dict[str, Any]:
    """
    Ranked search with pagination.

    ``scope_site``: workspace child name; boosts URLs under ``/local-site/<site>/``.
    Returns ``hits``, ``total``, ``limit``, ``offset``.
    """
    mq = build_fts_match_query(user_query)
    if mq is None:
        return {"hits": [], "total": 0, "limit": limit, "offset": offset}
    lim = max(1, min(limit, 100))
    off = max(0, offset)
    site = (scope_site or "").strip()
    scope_pat = f"/local-site/{site}/%" if site else ""

    count_sql = "SELECT COUNT(*) FROM search_fts WHERE search_fts MATCH ?"
    try:
        total = int(conn.execute(count_sql, (mq,)).fetchone()[0])
    except sqlite3.OperationalError:
        return {"hits": [], "total": 0, "limit": lim, "offset": off}

    # Snippet on body: columns path_key, url, title, headings, body, source -> index 4.
    # Paginate in SQL so OFFSET is correct at any depth (BM25 column weights favor title/headings).
    sql = """
        SELECT
          search_fts.path_key,
          search_fts.url,
          search_fts.title,
          search_fts.headings,
          search_fts.source,
          snippet(search_fts, 4, '[', ']', '…', 24) AS snippet,
          bm25(search_fts, ?, ?, ?) AS bm25_raw,
          COALESCE(i.ref_count, 0) AS ref_count
        FROM search_fts
        LEFT JOIN search_indegree i ON i.path_key = search_fts.path_key
        WHERE search_fts MATCH ?
        ORDER BY
          CASE WHEN ? != '' AND search_fts.url LIKE ? THEN 0 ELSE 1 END,
          (
            bm25(search_fts, ?, ?, ?)
            - ? * (LOG(1 + COALESCE(i.ref_count, 0)) / LOG(2))
          ),
          search_fts.path_key
        LIMIT ? OFFSET ?
    """
    params = (
        _BM25_W_TITLE,
        _BM25_W_HEADINGS,
        _BM25_W_BODY,
        mq,
        site,
        scope_pat,
        _BM25_W_TITLE,
        _BM25_W_HEADINGS,
        _BM25_W_BODY,
        _REF_COUNT_SCALE,
        lim,
        off,
    )
    try:
        rows = conn.execute(sql, params).fetchall()
    except sqlite3.OperationalError:
        return {"hits": [], "total": total, "limit": lim, "offset": off}

    out: list[dict[str, Any]] = []
    for row in rows:
        title_s = str(row["title"] or "")
        bm25_val = float(row["bm25_raw"])
        ref_c = int(row["ref_count"])
        ref_term = _REF_COUNT_SCALE * (math.log(1 + ref_c) / math.log(2))
        base = bm25_val - ref_term
        out.append(
            {
                "path_key": str(row["path_key"]),
                "url": str(row["url"]),
                "title": title_s,
                "source": str(row["source"]),
                "snippet": str(row["snippet"] or ""),
                "ref_count": ref_c,
                "score": round(base, 4),
            }
        )

    return {"hits": out, "total": total, "limit": lim, "offset": off}


def ingest_path_key(url: str) -> str:
    import hashlib

    h = hashlib.sha256(url.strip().encode("utf-8")).hexdigest()[:32]
    return f"ls:ingest:{h}"


def upsert_ingested(
    conn: sqlite3.Connection,
    *,
    url: str,
    title: str,
    body: str,
) -> None:
    import time

    pk = ingest_path_key(url)
    ns = time.time_ns()
    b = body.encode("utf-8")
    upsert_document(
        conn,
        path_key=pk,
        url=url.strip(),
        title=title,
        headings="",
        body=body,
        source=SOURCE_INGESTED,
        mtime_ns=ns,
        size_bytes=len(b),
    )
