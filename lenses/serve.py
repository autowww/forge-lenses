"""HTTP server: dynamic workspace UI, static /docs, JSON API."""

from __future__ import annotations

import argparse
import mimetypes
import urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from lenses.registry import load_registry
from lenses.render import (
    page_overview,
    page_projects,
    page_toolset,
    page_wbs,
    page_wbs_view,
    page_websites,
)
from lenses.scan import resolve_workspace_root, scan_workspace, workspace_state_json


LENSES_REPO_ROOT = Path(__file__).resolve().parent.parent
DOCS_DIR = LENSES_REPO_ROOT / "lenses-docs"


def _safe_wbs_file(workspace_root: Path, rel: str) -> Path | None:
    if not rel or ".." in rel.split("/") or rel.startswith(("/", "\\")):
        return None
    rel_norm = rel.replace("\\", "/").strip("/")
    candidate = (workspace_root / rel_norm).resolve()
    wr = workspace_root.resolve()
    try:
        candidate.relative_to(wr)
    except ValueError:
        return None
    parts = candidate.parts
    if "requirements" not in parts:
        return None
    if candidate.name not in ("WBS.md", "WBS.csv"):
        return None
    if not candidate.is_file():
        return None
    return candidate


def _safe_docs_path(url_path: str) -> Path | None:
    """Map /docs[/…] to files under lenses-docs/."""
    path_only = url_path.split("?", 1)[0]
    if not path_only.startswith("/docs"):
        return None
    rest = path_only[len("/docs") :].lstrip("/")
    if not rest:
        rest = "index.html"
    target = (DOCS_DIR / rest).resolve()
    docs_resolved = DOCS_DIR.resolve()
    try:
        target.relative_to(docs_resolved)
    except ValueError:
        return None
    if not target.is_file():
        return None
    return target


class LensesHandler(BaseHTTPRequestHandler):
    workspace_root: Path = Path(".")
    registry: dict = {}

    def log_message(self, fmt: str, *args: object) -> None:
        print(f"[lenses] {self.address_string()} - {fmt % args}")

    def _send(self, code: int, body: bytes, content_type: str) -> None:
        self.send_response(code)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _scan(self) -> dict:
        return scan_workspace(self.workspace_root, LENSES_REPO_ROOT, self.registry)

    def do_GET(self) -> None:  # noqa: N802
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path.rstrip("/") or "/"
        if path != "/" and parsed.path.endswith("/") and path != "/docs":
            path = parsed.path.rstrip("/") or "/"

        eu = self.registry.get("external_urls") or {}
        handbook_url = str(eu.get("handbook", "https://blueprints.forgesdlc.com/"))
        forge_url = str(eu.get("forge", "https://forgesdlc.com/"))

        if path == "/api/workspace-state":
            state = self._scan()
            raw = workspace_state_json(state).encode("utf-8")
            self._send(200, raw, "application/json; charset=utf-8")
            return

        if parsed.path.startswith("/docs"):
            doc_path = _safe_docs_path(parsed.path)
            if doc_path is None:
                self._send(
                    404,
                    b"Docs not built. Run: python3 generator/build-lenses-docs.py",
                    "text/plain; charset=utf-8",
                )
                return
            mime, _ = mimetypes.guess_type(str(doc_path))
            ctype = mime or "application/octet-stream"
            if doc_path.suffix.lower() == ".html":
                ctype = "text/html; charset=utf-8"
            data = doc_path.read_bytes()
            self._send(200, data, ctype)
            return

        state = self._scan()

        if path == "/":
            html = page_overview(state, handbook_url, forge_url).encode("utf-8")
            self._send(200, html, "text/html; charset=utf-8")
            return
        if path == "/projects":
            html = page_projects(state, handbook_url, forge_url).encode("utf-8")
            self._send(200, html, "text/html; charset=utf-8")
            return
        if path == "/toolset":
            html = page_toolset(state, handbook_url, forge_url).encode("utf-8")
            self._send(200, html, "text/html; charset=utf-8")
            return
        if path == "/websites":
            html = page_websites(state, self.registry, handbook_url, forge_url).encode(
                "utf-8"
            )
            self._send(200, html, "text/html; charset=utf-8")
            return
        if path == "/wbs":
            html = page_wbs(state, handbook_url, forge_url).encode("utf-8")
            self._send(200, html, "text/html; charset=utf-8")
            return
        if path == "/wbs/view":
            qs = urllib.parse.parse_qs(parsed.query or "")
            rels = qs.get("p", [])
            if not rels:
                self._send(400, b"Missing p=", "text/plain; charset=utf-8")
                return
            rel = rels[0]
            sp = _safe_wbs_file(self.workspace_root, rel)
            if sp is None:
                self._send(404, b"Not found or not allowed", "text/plain; charset=utf-8")
                return
            text = sp.read_text(encoding="utf-8", errors="replace")
            kind = "csv" if sp.suffix.lower() == ".csv" else "md"
            html = page_wbs_view(rel, text, kind, handbook_url, forge_url).encode("utf-8")
            self._send(200, html, "text/html; charset=utf-8")
            return

        self._send(404, b"Not found", "text/plain; charset=utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="lenses local workspace dashboard")
    parser.add_argument(
        "--workspace-root",
        type=Path,
        default=None,
        help="Directory containing sibling repos (default: parent of lenses checkout or LENSES_WORKSPACE_ROOT)",
    )
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8080)
    args = parser.parse_args()

    import os

    env_root = os.environ.get("LENSES_WORKSPACE_ROOT")
    ws = resolve_workspace_root(LENSES_REPO_ROOT, args.workspace_root, env_root)
    registry = load_registry(LENSES_REPO_ROOT)

    LensesHandler.workspace_root = ws
    LensesHandler.registry = registry

    server = ThreadingHTTPServer((args.host, args.port), LensesHandler)
    print(f"[lenses] http://{args.host}:{args.port}/")
    print(f"[lenses] workspace_root={ws}")
    print(f"[lenses] docs static from {DOCS_DIR} (run generator/build-lenses-docs.py if empty)")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n[lenses] stopped")


if __name__ == "__main__":
    main()
