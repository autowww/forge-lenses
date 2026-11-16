"""Tests for local SQLite FTS search (stdlib unittest)."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

# Run from repo root: PYTHONPATH=. python3 -m unittest discover -s tests -v


class TestSearchDb(unittest.TestCase):
    def test_build_fts_match_query(self) -> None:
        from lenses.search_db import build_fts_match_query

        self.assertIsNone(build_fts_match_query(""))
        self.assertIsNone(build_fts_match_query("   "))
        q = build_fts_match_query("hello world")
        self.assertIsNotNone(q)
        assert q is not None
        self.assertIn("AND", q)
        self.assertIn("hello", q)
        self.assertIn("world", q)

    def test_search_roundtrip(self) -> None:
        from lenses.search_db import SOURCE_LOCAL_SITE, connect, search, upsert_document

        tmp = Path(tempfile.mkdtemp())
        conn = connect(tmp)
        try:
            upsert_document(
                conn,
                path_key="ls:local_site:demo:index.html",
                url="/local-site/demo/index.html",
                title="Welcome",
                headings="Intro",
                body="The quick brown fox jumps over the lazy dog",
                source=SOURCE_LOCAL_SITE,
                mtime_ns=1,
                size_bytes=100,
            )
            conn.commit()
            out = search(conn, "fox dog", limit=10)
            hits = out["hits"]
            self.assertEqual(out["total"], 1)
            self.assertEqual(len(hits), 1)
            self.assertEqual(hits[0]["url"], "/local-site/demo/index.html")
            self.assertIn("fox", hits[0]["snippet"].lower())
        finally:
            conn.close()

    def test_search_headings_column(self) -> None:
        from lenses.search_db import SOURCE_LOCAL_SITE, connect, search, upsert_document

        tmp = Path(tempfile.mkdtemp())
        conn = connect(tmp)
        try:
            upsert_document(
                conn,
                path_key="ls:local_site:demo:page.html",
                url="/local-site/demo/page.html",
                title="No match here",
                headings="headingonlytoken xyz",
                body="other words",
                source=SOURCE_LOCAL_SITE,
                mtime_ns=1,
                size_bytes=80,
            )
            conn.commit()
            out = search(conn, "headingonlytoken", limit=5)
            self.assertGreaterEqual(out["total"], 1)
            self.assertEqual(out["hits"][0]["url"], "/local-site/demo/page.html")
        finally:
            conn.close()


class TestSearchCrawl(unittest.TestCase):
    def test_html_to_text_and_title(self) -> None:
        from lenses.search_crawl import html_to_text_and_title

        html = (
            b"<html><head><title>TT</title></head><body>"
            b"<h2>Section A</h2><p>Para one</p><script>x</script><h3>Sub</h3><p>Two</p></body></html>"
        )
        body, title, headings = html_to_text_and_title(html, 5000)
        self.assertEqual(title, "TT")
        self.assertIn("Section A", headings)
        self.assertIn("Sub", headings)
        self.assertIn("Para one", body)
        self.assertIn("Two", body)
        self.assertNotIn("script", body.lower())

    def test_reindex_minimal_workspace(self) -> None:
        """Indexes ``website/`` without ``firebase.json`` (local static output only)."""
        from lenses.search_crawl import reindex_workspace

        root = Path(tempfile.mkdtemp())
        site = root / "mysite"
        site.mkdir()
        pub = site / "website"
        pub.mkdir()
        (pub / "hello.html").write_text(
            "<!DOCTYPE html><html><head><title>X</title></head>"
            "<body><p>uniquewobbletoken</p></body></html>",
            encoding="utf-8",
        )
        lenses_root = Path(tempfile.mkdtemp())
        (lenses_root / "lenses-docs").mkdir(parents=True)
        (lenses_root / "lenses-docs" / "index.html").write_text(
            "<html><head><title>D</title></head><body>doctokenzzz</body></html>",
            encoding="utf-8",
        )
        reg: dict = {"ignore_paths": []}
        r = reindex_workspace(root, lenses_root, reg)
        self.assertTrue(r.get("ok"))
        self.assertGreaterEqual(int(r.get("indexed", 0)), 2)

        from lenses.search_db import connect, search

        conn = connect(root)
        try:
            h1 = search(conn, "uniquewobbletoken", limit=5)["hits"]
            self.assertTrue(any("local_site" in x.get("source", "") for x in h1))
            h2 = search(conn, "doctokenzzz", limit=5)["hits"]
            self.assertTrue(any("lenses_docs" in x.get("source", "") for x in h2))
        finally:
            conn.close()


class TestSearchRankingPagination(unittest.TestCase):
    def test_reindex_indegree_and_link_resolution(self) -> None:
        from lenses.search_crawl import reindex_workspace

        root = Path(tempfile.mkdtemp())
        site = root / "linkdemo"
        site.mkdir()
        pub = site / "website"
        pub.mkdir()
        (pub / "a.html").write_text(
            "<!DOCTYPE html><html><head><title>A</title></head>"
            '<body><p>alphalinktoken</p><a href="b.html">to b</a></body></html>',
            encoding="utf-8",
        )
        (pub / "b.html").write_text(
            "<!DOCTYPE html><html><head><title>B</title></head>"
            "<body><p>betalinktoken uniquechildtoken</p></body></html>",
            encoding="utf-8",
        )
        lenses_root = Path(tempfile.mkdtemp())
        (lenses_root / "lenses-docs").mkdir(parents=True)
        reg: dict = {"ignore_paths": []}
        r = reindex_workspace(root, lenses_root, reg)
        self.assertTrue(r.get("ok"))

        from lenses.search_db import connect, search

        conn = connect(root)
        try:
            b_hits = search(conn, "betalinktoken", limit=5)["hits"]
            b = next(x for x in b_hits if "b.html" in x.get("url", ""))
            self.assertGreaterEqual(int(b.get("ref_count", 0)), 1)
        finally:
            conn.close()

    def test_search_pagination_and_scope(self) -> None:
        from lenses.search_db import SOURCE_LOCAL_SITE, connect, search, upsert_document

        tmp = Path(tempfile.mkdtemp())
        conn = connect(tmp)
        try:
            triples = [
                ("ls:local_site:apple:a.html", "/local-site/apple/a.html", "apple"),
                ("ls:local_site:apple:b.html", "/local-site/apple/b.html", "apple"),
                ("ls:local_site:banana:x.html", "/local-site/banana/x.html", "banana"),
            ]
            for i, (pk, url, site) in enumerate(triples):
                upsert_document(
                    conn,
                    path_key=pk,
                    url=url,
                    title=f"T{i}",
                    headings="",
                    body=f"sharedtoken page{i} {site}",
                    source=SOURCE_LOCAL_SITE,
                    mtime_ns=i + 1,
                    size_bytes=50,
                )
            from lenses.search_db import set_indegree_counts

            set_indegree_counts(conn, {"ls:local_site:apple:a.html": 5})
            conn.commit()

            page1 = search(conn, "sharedtoken", limit=1, offset=0)
            self.assertEqual(page1["total"], 3)
            self.assertEqual(len(page1["hits"]), 1)
            page2 = search(conn, "sharedtoken", limit=1, offset=1)
            self.assertEqual(len(page2["hits"]), 1)
            self.assertNotEqual(
                page1["hits"][0]["path_key"], page2["hits"][0]["path_key"]
            )

            scoped = search(
                conn, "sharedtoken", limit=10, offset=0, scope_site="apple"
            )
            hits_scoped = scoped["hits"]
            self.assertGreaterEqual(len(hits_scoped), 2)
            self.assertIn("/local-site/apple/", hits_scoped[0]["url"])
            self.assertIn("/local-site/apple/", hits_scoped[1]["url"])
        finally:
            conn.close()


class TestResolveStaticSiteRoot(unittest.TestCase):
    def test_website_without_firebase(self) -> None:
        from lenses.scan import resolve_static_site_root

        root = Path(tempfile.mkdtemp())
        proj = root / "app"
        proj.mkdir()
        (proj / "website").mkdir(parents=True)
        (proj / "website" / "a.html").write_text("<html></html>", encoding="utf-8")
        got = resolve_static_site_root(proj)
        self.assertEqual(got, (proj / "website").resolve())

    def test_firebase_public_when_present(self) -> None:
        from lenses.scan import resolve_static_site_root

        root = Path(tempfile.mkdtemp())
        proj = root / "app"
        proj.mkdir()
        (proj / "firebase.json").write_text(
            json.dumps({"hosting": {"public": "out"}}), encoding="utf-8"
        )
        (proj / "out").mkdir(parents=True)
        (proj / "out" / "x.html").write_text("<html></html>", encoding="utf-8")
        got = resolve_static_site_root(proj)
        self.assertEqual(got, (proj / "out").resolve())

    def test_fallback_public_dir(self) -> None:
        from lenses.scan import resolve_static_site_root

        root = Path(tempfile.mkdtemp())
        proj = root / "app"
        proj.mkdir()
        (proj / "public").mkdir(parents=True)
        (proj / "public" / "index.html").write_text("<html></html>", encoding="utf-8")
        got = resolve_static_site_root(proj)
        self.assertEqual(got, (proj / "public").resolve())


class TestSearchIngest(unittest.TestCase):
    def test_ingest_path_stable(self) -> None:
        from lenses.search_db import connect, ingest_path_key, search, upsert_ingested

        tmp = Path(tempfile.mkdtemp())
        conn = connect(tmp)
        try:
            k1 = ingest_path_key("http://example.com/a")
            k2 = ingest_path_key("http://example.com/a")
            self.assertEqual(k1, k2)
            upsert_ingested(conn, url="http://example.com/a", title="T", body="dynamic content")
            conn.commit()
            out = search(conn, "dynamic content", limit=5)
            hits = out["hits"]
            self.assertEqual(len(hits), 1)
            self.assertEqual(hits[0]["source"], "ingested")
        finally:
            conn.close()
