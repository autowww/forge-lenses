"""HTTP server: dynamic workspace UI, static /docs, JSON API."""

from __future__ import annotations

import argparse
import copy
import ipaddress
import json
import mimetypes
import os
import sys
import threading
import time
import urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from lenses.auth_session import SESSION_COOKIE, SESSION_MAX_AGE_SEC, SessionManager, verify_github_token
from lenses.local_site_html import (
    build_local_site_base_href,
    content_type_for_local_site_file,
    inject_base_and_rewrite_local_site_html,
    local_site_directory_url_path,
)
from lenses.expected_github import resolve_expected_github_login
from lenses.board_preview import schedule_board_preview_capture
from lenses.git_actions import (
    client_may_run_git_actions,
    client_may_write_sticker_board,
    run_git_action,
)
from lenses.sticker_board import (
    MAX_BODY_BYTES as STICKER_BOARD_MAX_BODY_BYTES,
    UNASSIGNED_PROJECT_KEY,
    board_preview_path,
    find_board_entry,
    is_valid_board_id,
    load_board,
    load_registry_raw,
    normalize_board,
    registry_apply,
    registry_snapshot,
    save_board,
    validate_board,
)
from lenses.project_stats import collect_project_stats
from lenses.registry import load_registry
from lenses.render import (
    page_overview,
    page_project_detail,
    page_project_repo_strategy,
    page_projects,
    page_roadmap_preview_document,
    page_roadmap_timeline_document,
    page_roadmaps,
    roadmap_summary_fragment,
    page_sticker_board_editor,
    page_sticker_board_hub,
    page_toolset,
    page_toolset_run,
    page_tutorials,
    page_wbs,
    page_wbs_view,
    page_websites,
    page_websites_browse,
)
from lenses.roadmap_outline import outline_json, parse_roadmap_markdown
from lenses.scan import (
    parse_firebase_hosting,
    resolve_workspace_child_dir,
    resolve_workspace_root,
    scan_workspace,
    workspace_state_json,
)
from lenses.standards_compliance import enrich_workspace_with_standards
from lenses.tutorial_index import (
    repo_tutorials_url_tail_matches,
    resolve_repo_tutorials_site_file,
    resolve_tutorial_site_file,
    tutorial_url_tail_matches,
)
from lenses.shell_actions import client_may_run_shell_actions, run_allowlisted_action
from lenses.toolset_actions import run_toolset_script


LENSES_REPO_ROOT = Path(__file__).resolve().parent.parent
DOCS_DIR = LENSES_REPO_ROOT / "lenses-docs"

_DEFAULT_SCAN_CACHE_SEC = 3.0
_scan_cache_lock = threading.Lock()
# Key: git_extended only (workspace is fixed per process). Value: (state dict, monotonic time).
_scan_cache_store: dict[tuple[bool], tuple[dict, float]] = {}


def _scan_cache_ttl_sec() -> float | None:
    """TTL for workspace scan cache; None disables caching. Env LENSES_SCAN_CACHE_SEC: 0=off, empty=default."""
    raw = os.environ.get("LENSES_SCAN_CACHE_SEC", "").strip()
    if raw == "":
        return _DEFAULT_SCAN_CACHE_SEC
    try:
        v = float(raw)
    except ValueError:
        return _DEFAULT_SCAN_CACHE_SEC
    if v <= 0:
        return None
    return v


def _refresh_query_truthy(qs: dict[str, list[str]]) -> bool:
    vals = qs.get("refresh", [])
    if not vals:
        return False
    return str(vals[0]).strip().lower() in ("1", "true", "yes")


def _board_preview_base_url(handler: BaseHTTPRequestHandler) -> str:
    _addr, port = handler.server.server_address
    return f"http://127.0.0.1:{port}"


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


def _safe_roadmap_file(workspace_root: Path, rel: str) -> Path | None:
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
    if "docs" not in parts:
        return None
    if candidate.name != "ROADMAP.md":
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


def _ks_under(base: Path, candidate: Path) -> bool:
    try:
        candidate.relative_to(base.resolve())
        return True
    except ValueError:
        return False


def _safe_ks_file(lenses_repo_root: Path, url_path: str) -> Path | None:
    """Map /__ks/… to files under kitchensink/css, js, or assets/svg."""
    path_only = url_path.split("?", 1)[0]
    if not path_only.startswith("/__ks/"):
        return None
    rest = path_only[len("/__ks/") :].lstrip("/").replace("\\", "/")
    if not rest or ".." in rest.split("/"):
        return None
    ks = (lenses_repo_root / "kitchensink").resolve()
    if not ks.is_dir():
        return None
    candidate = (ks / rest).resolve()
    try:
        candidate.relative_to(ks)
    except ValueError:
        return None
    allowed = (
        _ks_under(ks / "css", candidate),
        _ks_under(ks / "js", candidate),
        _ks_under(ks / "assets" / "svg", candidate),
    )
    if not any(allowed):
        return None
    if not candidate.is_file():
        return None
    return candidate


def _safe_lenses_static_file(lenses_repo_root: Path, url_path: str) -> Path | None:
    """Map /__lenses/… to files under lenses/static/ (js only for now)."""
    path_only = url_path.split("?", 1)[0]
    if not path_only.startswith("/__lenses/"):
        return None
    rest = path_only[len("/__lenses/") :].lstrip("/").replace("\\", "/")
    if not rest or ".." in rest.split("/"):
        return None
    static_root = (lenses_repo_root / "lenses" / "static").resolve()
    if not static_root.is_dir():
        return None
    candidate = (static_root / rest).resolve()
    try:
        candidate.relative_to(static_root)
    except ValueError:
        return None
    if not _ks_under(static_root / "js", candidate):
        return None
    if candidate.suffix.lower() != ".js":
        return None
    if not candidate.is_file():
        return None
    return candidate


def _child_slugs_from_scan(state: dict) -> set[str]:
    slugs: set[str] = {UNASSIGNED_PROJECT_KEY}
    for c in state.get("children") or []:
        if isinstance(c, dict):
            n = str(c.get("name", "")).strip()
            if n:
                slugs.add(n)
    return slugs


def _host_needs_bind_all_ack(host: str) -> bool:
    h = (host or "").strip()
    if h in ("0.0.0.0", "::"):
        return True
    if h in ("127.0.0.1", "localhost", "::1"):
        return False
    try:
        return not ipaddress.ip_address(h).is_loopback
    except ValueError:
        return False


def _firebase_public_dir(
    workspace_root: Path, registry: dict, site_name: str
) -> Path | None:
    child = resolve_workspace_child_dir(workspace_root, site_name, registry)
    if child is None:
        return None
    fb = child / "firebase.json"
    if not fb.is_file():
        return None
    pub, _ = parse_firebase_hosting(fb)
    base = (child / pub).resolve()
    child_res = child.resolve()
    try:
        base.relative_to(child_res)
    except ValueError:
        return None
    if not base.is_dir():
        return None
    return base


def _safe_local_site_file(
    workspace_root: Path, registry: dict, site_name: str, rel_path: str
) -> Path | None:
    child = resolve_workspace_child_dir(workspace_root, site_name, registry)
    if child is None:
        return None
    rel = (rel_path or "").strip().replace("\\", "/").lstrip("/")
    if ".." in rel.split("/"):
        return None
    if tutorial_url_tail_matches(rel):
        return resolve_tutorial_site_file(child, rel)
    if repo_tutorials_url_tail_matches(rel):
        hit = resolve_repo_tutorials_site_file(child, rel)
        if hit is not None:
            return hit
        # e.g. tutorials/ only under hosting.public with a nonstandard layout
    base = _firebase_public_dir(workspace_root, registry, site_name)
    if base is None:
        return None
    rel_fb = rel if rel else "index.html"
    candidate = (base / rel_fb).resolve()
    try:
        candidate.relative_to(base)
    except ValueError:
        return None
    if not candidate.is_file():
        return None
    return candidate


def _local_site_site_and_tail(path: str) -> tuple[str, str] | None:
    path_only = path.split("?", 1)[0]
    if not path_only.startswith("/local-site/"):
        return None
    rest = path_only[len("/local-site/") :].lstrip("/")
    if not rest:
        return None
    site, _, tail = rest.partition("/")
    site = urllib.parse.unquote(site)
    if not site:
        return None
    return site, tail


def _cookie_value(cookie_header: str | None, name: str) -> str | None:
    if not cookie_header:
        return None
    for part in cookie_header.split(";"):
        k, _, v = part.strip().partition("=")
        if k.strip() == name:
            return v.strip() or None
    return None


def _parse_api_project_subpath(path: str) -> tuple[str, str] | None:
    """Return (project_name, tail) for /api/project/<name>/<tail> or None."""
    p = path.split("?", 1)[0].rstrip("/")
    prefix = "/api/project/"
    if not p.startswith(prefix):
        return None
    rest = p[len(prefix) :].lstrip("/")
    if not rest:
        return None
    slash = rest.find("/")
    if slash < 0:
        return None
    name = urllib.parse.unquote(rest[:slash])
    tail = rest[slash + 1 :]
    if not name or not tail or "/" in tail:
        return None
    return name, tail


class LensesHandler(BaseHTTPRequestHandler):
    workspace_root: Path = Path(".")
    registry: dict = {}
    expected_github_login: str | None = None
    session_manager: SessionManager | None = None

    def log_message(self, fmt: str, *args: object) -> None:
        print(f"[lenses] {self.address_string()} - {fmt % args}")

    def _send(self, code: int, body: bytes, content_type: str) -> None:
        self.send_response(code)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_json(
        self,
        code: int,
        obj: object,
        *,
        set_cookie: str | None = None,
    ) -> None:
        raw = json.dumps(obj, indent=2, sort_keys=True).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(raw)))
        if set_cookie:
            self.send_header("Set-Cookie", set_cookie)
        self.end_headers()
        self.wfile.write(raw)

    def _scan(
        self, *, git_extended: bool = False, force_refresh: bool = False
    ) -> dict:
        """Full workspace scan + standards enrichment. Cached briefly (see LENSES_SCAN_CACHE_SEC)."""
        ttl = _scan_cache_ttl_sec()
        key = (git_extended,)
        if ttl is not None and not force_refresh:
            now = time.monotonic()
            with _scan_cache_lock:
                hit = _scan_cache_store.get(key)
                if hit is not None:
                    state_cached, t0 = hit
                    if now - t0 < ttl:
                        return copy.deepcopy(state_cached)

        state = scan_workspace(
            self.workspace_root,
            LENSES_REPO_ROOT,
            self.registry,
            git_extended=git_extended,
        )
        enrich_workspace_with_standards(state, self.registry)
        if ttl is not None:
            with _scan_cache_lock:
                _scan_cache_store[key] = (state, time.monotonic())
        return copy.deepcopy(state)

    def do_GET(self) -> None:  # noqa: N802
        parsed = urllib.parse.urlparse(self.path)
        qs = urllib.parse.parse_qs(parsed.query or "")
        force_refresh = _refresh_query_truthy(qs)
        path = parsed.path.rstrip("/") or "/"
        if path != "/" and parsed.path.endswith("/") and not parsed.path.startswith("/docs"):
            path = parsed.path.rstrip("/") or "/"

        eu = self.registry.get("external_urls") or {}
        handbook_url = str(eu.get("handbook", "https://blueprints.forgesdlc.com/"))
        forge_url = str(eu.get("forge", "https://forgesdlc.com/"))

        ks_file = _safe_ks_file(LENSES_REPO_ROOT, parsed.path)
        if ks_file is not None:
            mime, _ = mimetypes.guess_type(str(ks_file))
            ctype = mime or "application/octet-stream"
            if ks_file.suffix.lower() == ".css":
                ctype = "text/css; charset=utf-8"
            elif ks_file.suffix.lower() == ".js":
                ctype = "text/javascript; charset=utf-8"
            elif ks_file.suffix.lower() == ".svg":
                ctype = "image/svg+xml; charset=utf-8"
            data = ks_file.read_bytes()
            self._send(200, data, ctype)
            return

        lens_static = _safe_lenses_static_file(LENSES_REPO_ROOT, parsed.path)
        if lens_static is not None:
            data = lens_static.read_bytes()
            self._send(200, data, "text/javascript; charset=utf-8")
            return

        if path == "/api/sticker-board":
            qs = urllib.parse.parse_qs(parsed.query or "")
            bid_qs = qs.get("board_id", [])
            board_id = str(bid_qs[0]).strip() if bid_qs else ""
            if not is_valid_board_id(board_id):
                self._send_json(
                    400,
                    {"ok": False, "error": "missing_or_invalid_board_id"},
                )
                return
            board = load_board(
                self.workspace_root, self.expected_github_login, board_id
            )
            if board.get("board_not_found"):
                self._send_json(
                    404,
                    {"ok": False, "error": "board_not_found"},
                )
                return
            board.pop("board_not_found", None)
            raw = json.dumps(board, indent=2, sort_keys=True).encode("utf-8")
            self._send(200, raw, "application/json; charset=utf-8")
            return

        if path == "/api/sticker-board-registry":
            state = self._scan(force_refresh=force_refresh)
            slugs = _child_slugs_from_scan(state)
            snap = registry_snapshot(
                self.workspace_root, self.expected_github_login, slugs
            )
            snap["shared_login_configured"] = bool(self.expected_github_login)
            snap["workspace_projects"] = sorted(
                p for p in slugs if p != UNASSIGNED_PROJECT_KEY
            )
            raw = json.dumps(snap, indent=2, sort_keys=True).encode("utf-8")
            self._send(200, raw, "application/json; charset=utf-8")
            return

        if path == "/api/roadmap-outline":
            qs = urllib.parse.parse_qs(parsed.query or "")
            rels = qs.get("p", [])
            if not rels:
                self._send(400, b"Missing p=", "text/plain; charset=utf-8")
                return
            rel = rels[0]
            sp = _safe_roadmap_file(self.workspace_root, rel)
            if sp is None:
                self._send(404, b"Not found or not allowed", "text/plain; charset=utf-8")
                return
            text = sp.read_text(encoding="utf-8", errors="replace")
            parsed = parse_roadmap_markdown(text)
            raw = outline_json(parsed).encode("utf-8")
            self._send(200, raw, "application/json; charset=utf-8")
            return

        if path == "/api/workspace-state":
            ext = qs.get("git_extended", [])
            git_extended = bool(ext) and str(ext[0]).lower() in ("1", "true", "yes")
            state = self._scan(
                git_extended=git_extended, force_refresh=force_refresh
            )
            raw = workspace_state_json(state).encode("utf-8")
            self._send(200, raw, "application/json; charset=utf-8")
            return

        if path == "/api/auth/status":
            sm = self.session_manager
            exp = self.expected_github_login
            ck = _cookie_value(self.headers.get("Cookie"), SESSION_COOKIE)
            sess_login = sm.session_login(ck) if sm else None
            session_ok = bool(
                exp and sess_login and sess_login.lower() == exp.lower()
            )
            actions = self.registry.get("actions") or {}
            sites_with_actions = sorted(
                k for k, v in actions.items() if isinstance(v, dict) and v
            )
            action_keys_by_site: dict[str, list[str]] = {}
            for sk, spec in actions.items():
                if not isinstance(spec, dict):
                    continue
                keys = sorted(k for k, v in spec.items() if isinstance(v, dict) and v.get("argv"))
                if keys:
                    action_keys_by_site[str(sk)] = keys
            self._send_json(
                200,
                {
                    "expected_login": exp,
                    "expected_configured": bool(exp),
                    "session_login": sess_login,
                    "session_ok": session_ok,
                    "sites_with_allowlisted_actions": sites_with_actions,
                    "action_keys_by_site": action_keys_by_site,
                },
            )
            return

        if parsed.path.startswith("/local-site/"):
            lp = _local_site_site_and_tail(parsed.path)
            if lp is None:
                self._send(404, b"Not found", "text/plain; charset=utf-8")
                return
            site_name, tail = lp
            sf = _safe_local_site_file(
                self.workspace_root, self.registry, site_name, tail
            )
            if sf is None:
                self._send(404, b"Not found", "text/plain; charset=utf-8")
                return
            ctype = content_type_for_local_site_file(sf)
            data = sf.read_bytes()
            if ctype.startswith("text/html"):
                path_only = parsed.path.split("?", 1)[0]
                scheme = (
                    "https"
                    if self.headers.get("X-Forwarded-Proto", "")
                    .lower()
                    .startswith("https")
                    else "http"
                )
                host = (self.headers.get("Host") or "").strip() or "127.0.0.1"
                dir_path = local_site_directory_url_path(path_only)
                base_href = build_local_site_base_href(
                    scheme=scheme, host=host, directory_url_path=dir_path
                )
                data = inject_base_and_rewrite_local_site_html(
                    data, base_href=base_href, site_name=site_name
                )
            self._send(200, data, ctype)
            return

        api_proj = _parse_api_project_subpath(parsed.path)
        if api_proj is not None:
            name, tail = api_proj
            if tail == "stats":
                child_path = resolve_workspace_child_dir(
                    self.workspace_root, name, self.registry
                )
                if child_path is None or not (child_path / ".git").exists():
                    self._send(
                        404,
                        b'{"error":"not_found"}',
                        "application/json; charset=utf-8",
                    )
                    return
                stats = collect_project_stats(child_path)
                raw = json.dumps(stats, indent=2, sort_keys=True).encode("utf-8")
                self._send(200, raw, "application/json; charset=utf-8")
                return
            err = json.dumps({"error": "not_found"}).encode("utf-8")
            self._send(404, err, "application/json; charset=utf-8")
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

        state = self._scan(git_extended=True, force_refresh=force_refresh)

        if path == "/":
            html = page_overview(
                state,
                self.registry,
                handbook_url,
                forge_url,
                LENSES_REPO_ROOT,
            ).encode("utf-8")
            self._send(200, html, "text/html; charset=utf-8")
            return
        if path == "/projects":
            html = page_projects(
                state,
                self.registry,
                handbook_url,
                forge_url,
                LENSES_REPO_ROOT,
            ).encode("utf-8")
            self._send(200, html, "text/html; charset=utf-8")
            return
        if path == "/tutorials":
            html = page_tutorials(
                state,
                self.registry,
                handbook_url,
                forge_url,
                LENSES_REPO_ROOT,
            ).encode("utf-8")
            self._send(200, html, "text/html; charset=utf-8")
            return

        if path.startswith("/projects/"):
            rest = parsed.path[len("/projects/") :].strip("/")
            segments = [urllib.parse.unquote(s) for s in rest.split("/") if s]
            if not segments:
                self._send(404, b"Unknown project", "text/plain; charset=utf-8")
                return
            project_name = segments[0]
            if len(segments) >= 2:
                sub = segments[1].strip().lower()
                if sub != "strategy":
                    self._send(404, b"Not found", "text/plain; charset=utf-8")
                    return
            child_path = resolve_workspace_child_dir(
                self.workspace_root, project_name, self.registry
            )
            if child_path is None:
                self._send(404, b"Unknown project", "text/plain; charset=utf-8")
                return
            if len(segments) >= 2:
                html = page_project_repo_strategy(
                    state,
                    self.registry,
                    project_name,
                    child_path,
                    handbook_url,
                    forge_url,
                    LENSES_REPO_ROOT,
                ).encode("utf-8")
            else:
                html = page_project_detail(
                    state,
                    self.registry,
                    project_name,
                    child_path,
                    handbook_url,
                    forge_url,
                    LENSES_REPO_ROOT,
                ).encode("utf-8")
            self._send(200, html, "text/html; charset=utf-8")
            return

        if path.startswith("/toolset/"):
            rest = path[len("/toolset/") :].lstrip("/")
            if not rest or "/" in rest:
                self._send(404, b"Not found", "text/plain; charset=utf-8")
                return
            script_name = urllib.parse.unquote(rest)
            html = page_toolset_run(
                state,
                script_name,
                self.workspace_root,
                handbook_url,
                forge_url,
                LENSES_REPO_ROOT,
            ).encode("utf-8")
            self._send(200, html, "text/html; charset=utf-8")
            return
        if path == "/toolset":
            html = page_toolset(
                state, handbook_url, forge_url, LENSES_REPO_ROOT
            ).encode("utf-8")
            self._send(200, html, "text/html; charset=utf-8")
            return
        if path == "/websites":
            html = page_websites(
                state,
                self.registry,
                handbook_url,
                forge_url,
                LENSES_REPO_ROOT,
            ).encode("utf-8")
            self._send(200, html, "text/html; charset=utf-8")
            return
        if path == "/websites/browse":
            qs = urllib.parse.parse_qs(parsed.query or "")
            sites = qs.get("site", [])
            site_name = sites[0] if sites else ""
            if not site_name:
                self._send(400, b"Missing site=", "text/plain; charset=utf-8")
                return
            if _firebase_public_dir(self.workspace_root, self.registry, site_name) is None:
                self._send(404, b"Unknown site", "text/plain; charset=utf-8")
                return
            html = page_websites_browse(
                state,
                self.registry,
                site_name,
                handbook_url,
                forge_url,
                LENSES_REPO_ROOT,
            ).encode("utf-8")
            self._send(200, html, "text/html; charset=utf-8")
            return
        if path == "/wbs":
            html = page_wbs(
                state, handbook_url, forge_url, LENSES_REPO_ROOT
            ).encode("utf-8")
            self._send(200, html, "text/html; charset=utf-8")
            return
        if path == "/roadmaps":
            html = page_roadmaps(
                state, handbook_url, forge_url, LENSES_REPO_ROOT
            ).encode("utf-8")
            self._send(200, html, "text/html; charset=utf-8")
            return
        if path == "/roadmaps/summary":
            qs = urllib.parse.parse_qs(parsed.query or "")
            rels = qs.get("p", [])
            if not rels:
                self._send(400, b"Missing p=", "text/plain; charset=utf-8")
                return
            rel = rels[0]
            sp = _safe_roadmap_file(self.workspace_root, rel)
            if sp is None:
                self._send(404, b"Not found or not allowed", "text/plain; charset=utf-8")
                return
            text = sp.read_text(encoding="utf-8", errors="replace")
            frag = roadmap_summary_fragment(text)
            self._send(200, frag.encode("utf-8"), "text/html; charset=utf-8")
            return
        if path == "/roadmaps/timeline":
            qs = urllib.parse.parse_qs(parsed.query or "")
            rels = qs.get("p", [])
            if not rels:
                self._send(400, b"Missing p=", "text/plain; charset=utf-8")
                return
            rel = rels[0]
            sp = _safe_roadmap_file(self.workspace_root, rel)
            if sp is None:
                self._send(404, b"Not found or not allowed", "text/plain; charset=utf-8")
                return
            text = sp.read_text(encoding="utf-8", errors="replace")
            doc = page_roadmap_timeline_document(text, rel)
            self._send(200, doc.encode("utf-8"), "text/html; charset=utf-8")
            return
        if path == "/roadmaps/preview":
            qs = urllib.parse.parse_qs(parsed.query or "")
            rels = qs.get("p", [])
            secs = qs.get("section", [])
            if not rels or not secs:
                self._send(400, b"Missing p= or section=", "text/plain; charset=utf-8")
                return
            rel = rels[0]
            section_id = secs[0]
            sp = _safe_roadmap_file(self.workspace_root, rel)
            if sp is None:
                self._send(404, b"Not found or not allowed", "text/plain; charset=utf-8")
                return
            text = sp.read_text(encoding="utf-8", errors="replace")
            doc = page_roadmap_preview_document(rel, section_id, text)
            self._send(200, doc.encode("utf-8"), "text/html; charset=utf-8")
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
            html = page_wbs_view(
                rel,
                text,
                kind,
                handbook_url,
                forge_url,
                LENSES_REPO_ROOT,
            ).encode("utf-8")
            self._send(200, html, "text/html; charset=utf-8")
            return
        if path.startswith("/board-preview/") and path.endswith(".png"):
            rest_png = path[len("/board-preview/") :]
            stem = rest_png[: -4] if len(rest_png) > 4 else ""
            board_id = urllib.parse.unquote(stem.strip()) if stem else ""
            if not board_id or "/" in board_id or not is_valid_board_id(board_id):
                self._send(404, b"Not found", "text/plain; charset=utf-8")
                return
            reg = load_registry_raw(self.workspace_root)
            if find_board_entry(reg, board_id) is None:
                self._send(404, b"Not found", "text/plain; charset=utf-8")
                return
            fp = board_preview_path(self.workspace_root, board_id)
            if not fp.is_file():
                self._send(404, b"Not found", "text/plain; charset=utf-8")
                return
            data = fp.read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", "image/png")
            self.send_header("Content-Length", str(len(data)))
            self.send_header("Cache-Control", "private, max-age=60")
            self.send_header("ETag", f'"{int(fp.stat().st_mtime)}"')
            self.end_headers()
            self.wfile.write(data)
            return
        if path.startswith("/board/"):
            rest = path[len("/board/") :].strip()
            board_id = urllib.parse.unquote(rest) if rest else ""
            if not board_id or "/" in board_id or not is_valid_board_id(board_id):
                self._send(404, b"Not found", "text/plain; charset=utf-8")
                return
            reg = load_registry_raw(self.workspace_root)
            found = find_board_entry(reg, board_id)
            board_label = (
                str(found[1].get("label", "Board")).strip() or "Board"
                if found
                else "Board"
            )
            qs_board = urllib.parse.parse_qs(parsed.query or "")
            thumb_qs = qs_board.get("thumb", [])
            thumb_capture = bool(thumb_qs) and str(thumb_qs[0]).strip().lower() in (
                "1",
                "true",
                "yes",
            )
            html = page_sticker_board_editor(
                state,
                handbook_url,
                forge_url,
                LENSES_REPO_ROOT,
                bool(self.expected_github_login),
                board_id,
                board_label,
                thumb_capture=thumb_capture,
            ).encode("utf-8")
            self._send(200, html, "text/html; charset=utf-8")
            return

        if path == "/board":
            qs = urllib.parse.parse_qs(parsed.query or "")
            pre_proj = qs.get("project", [])
            project_filter = (
                str(pre_proj[0]).strip() if pre_proj else ""
            )
            html = page_sticker_board_hub(
                state,
                handbook_url,
                forge_url,
                LENSES_REPO_ROOT,
                bool(self.expected_github_login),
                project_filter,
            ).encode("utf-8")
            self._send(200, html, "text/html; charset=utf-8")
            return

        self._send(404, b"Not found", "text/plain; charset=utf-8")

    def do_POST(self) -> None:  # noqa: N802
        parsed = urllib.parse.urlparse(self.path)
        post_path = parsed.path.rstrip("/") or "/"

        if post_path == "/api/auth/github":
            self._post_api_auth_github()
            return
        if post_path == "/api/auth/logout":
            self._post_api_auth_logout()
            return
        if post_path == "/api/actions/run":
            self._post_api_actions_run()
            return
        if post_path == "/api/sticker-board":
            self._post_api_sticker_board(parsed)
            return
        if post_path == "/api/sticker-board-registry":
            self._post_api_sticker_board_registry()
            return
        if post_path == "/api/toolset/run":
            self._post_api_toolset_run()
            return

        api_proj = _parse_api_project_subpath(parsed.path)
        if api_proj is None or api_proj[1] != "git":
            self._send(404, b"Not found", "text/plain; charset=utf-8")
            return

        name, _tail = api_proj
        client_ip = self.client_address[0]
        if not client_may_run_git_actions(client_ip):
            msg = json.dumps(
                {
                    "ok": False,
                    "error": "Git actions allowed from loopback only, or set LENSES_ALLOW_GIT_ACTIONS=1",
                    "stdout": "",
                    "stderr": "",
                    "exit_code": -1,
                }
            ).encode("utf-8")
            self._send(403, msg, "application/json; charset=utf-8")
            return

        child_path = resolve_workspace_child_dir(
            self.workspace_root, name, self.registry
        )
        if child_path is None or not (child_path / ".git").exists():
            msg = json.dumps(
                {
                    "ok": False,
                    "error": "not_found",
                    "stdout": "",
                    "stderr": "",
                    "exit_code": -1,
                }
            ).encode("utf-8")
            self._send(404, msg, "application/json; charset=utf-8")
            return

        length = int(self.headers.get("Content-Length", "0") or "0")
        raw_body = self.rfile.read(length) if length > 0 else b"{}"
        try:
            body = json.loads(raw_body.decode("utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError):
            body = {}
        action = str(body.get("action", "")).strip()

        result = run_git_action(child_path, action)
        out = json.dumps(result, indent=2, sort_keys=True).encode("utf-8")
        code = 200 if result.get("ok") else 400
        self._send(code, out, "application/json; charset=utf-8")

    def _read_json_body(self, max_len: int = 256_000) -> dict[str, object]:
        length = int(self.headers.get("Content-Length", "0") or "0")
        if length <= 0 or length > max_len:
            return {}
        raw = self.rfile.read(length)
        try:
            data = json.loads(raw.decode("utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError):
            return {}
        return data if isinstance(data, dict) else {}

    def _post_api_auth_github(self) -> None:
        client_ip = self.client_address[0]
        if not client_may_run_shell_actions(client_ip):
            self._send_json(
                403,
                {"ok": False, "error": "GitHub auth allowed from loopback only (or set LENSES_ALLOW_ACTIONS=1)"},
            )
            return
        exp = self.expected_github_login
        if not exp:
            self._send_json(
                400,
                {
                    "ok": False,
                    "error": "expected_github_login_not_configured",
                    "hint": "Set github_login in workspace-registry.json, use a single .lenses-repo/<login>/ folder, or run gh auth login from the workspace.",
                },
            )
            return
        body = self._read_json_body()
        token = str(body.get("token", "")).strip()
        login, err = verify_github_token(token)
        if not login:
            self._send_json(
                401,
                {"ok": False, "error": "github_token_invalid", "detail": err or ""},
            )
            return
        if login.lower() != exp.lower():
            self._send_json(
                403,
                {
                    "ok": False,
                    "error": "github_login_mismatch",
                    "github_login": login,
                    "expected_login": exp,
                },
            )
            return
        sm = self.session_manager
        if sm is None:
            self._send_json(500, {"ok": False, "error": "session_store_unavailable"})
            return
        sid = sm.create_session(login)
        cookie = (
            f"{SESSION_COOKIE}={sid}; HttpOnly; SameSite=Lax; Path=/; "
            f"Max-Age={SESSION_MAX_AGE_SEC}"
        )
        self._send_json(200, {"ok": True, "login": login}, set_cookie=cookie)

    def _post_api_auth_logout(self) -> None:
        sm = self.session_manager
        ck = _cookie_value(self.headers.get("Cookie"), SESSION_COOKIE)
        if sm and ck:
            sm.clear_session(ck)
        clear = f"{SESSION_COOKIE}=; HttpOnly; SameSite=Lax; Path=/; Max-Age=0"
        self._send_json(200, {"ok": True}, set_cookie=clear)

    def _post_api_actions_run(self) -> None:
        client_ip = self.client_address[0]
        if not client_may_run_shell_actions(client_ip):
            self._send_json(
                403,
                {"ok": False, "error": "actions_allowed_from_loopback_only"},
            )
            return
        exp = self.expected_github_login
        sm = self.session_manager
        ck = _cookie_value(self.headers.get("Cookie"), SESSION_COOKIE)
        sess_login = sm.session_login(ck) if sm else None
        if not exp or not sess_login or sess_login.lower() != exp.lower():
            self._send_json(
                403,
                {
                    "ok": False,
                    "error": "auth_required",
                    "hint": "POST /api/auth/github with a PAT for the same user as this workspace.",
                },
            )
            return
        body = self._read_json_body()
        site = str(body.get("site", "")).strip()
        action = str(body.get("action", "")).strip()
        if not site or not action:
            self._send_json(400, {"ok": False, "error": "missing_site_or_action"})
            return
        actions = self.registry.get("actions") or {}
        site_spec = actions.get(site)
        if not isinstance(site_spec, dict):
            self._send_json(404, {"ok": False, "error": "site_not_in_allowlist"})
            return
        spec = site_spec.get(action)
        if not isinstance(spec, dict):
            self._send_json(404, {"ok": False, "error": "action_not_in_allowlist"})
            return
        argv = spec.get("argv")
        cwd_rel = str(spec.get("cwd_relative", "."))
        if not isinstance(argv, list):
            self._send_json(400, {"ok": False, "error": "invalid_registry_action"})
            return
        argv_s = [str(x) for x in argv]
        result = run_allowlisted_action(
            self.workspace_root, cwd_rel, argv_s, timeout_sec=900
        )
        self._send_json(200, {"ok": result.get("ok"), **result})

    def _post_api_sticker_board(self, parsed: urllib.parse.ParseResult) -> None:
        client_ip = self.client_address[0]
        if not client_may_write_sticker_board(client_ip):
            self._send_json(
                403,
                {
                    "ok": False,
                    "error": (
                        "Sticker board saves allowed from loopback only, "
                        "or set LENSES_ALLOW_GIT_ACTIONS=1"
                    ),
                },
            )
            return
        qs = urllib.parse.parse_qs(parsed.query or "")
        bid_qs = qs.get("board_id", [])
        board_id = str(bid_qs[0]).strip() if bid_qs else ""
        if not is_valid_board_id(board_id):
            self._send_json(
                400,
                {"ok": False, "error": "missing_or_invalid_board_id"},
            )
            return
        body = self._read_json_body(max_len=STICKER_BOARD_MAX_BODY_BYTES)
        if not body:
            self._send_json(
                400,
                {"ok": False, "error": "invalid_or_oversized_json"},
            )
            return
        body.pop("board_id", None)
        ok, err = validate_board(body, self.expected_github_login)
        if not ok:
            self._send_json(400, {"ok": False, "error": err})
            return
        try:
            normalized = normalize_board(body, self.expected_github_login)
            save_board(
                self.workspace_root,
                normalized,
                self.expected_github_login,
                board_id,
            )
        except ValueError as exc:
            err_s = str(exc)
            if err_s == "board_not_found":
                self._send_json(400, {"ok": False, "error": "board_not_found"})
            elif err_s == "invalid_board_id":
                self._send_json(400, {"ok": False, "error": "invalid_board_id"})
            else:
                self._send_json(
                    400,
                    {"ok": False, "error": "shared_board_login_required"},
                )
            return
        except OSError as exc:
            self._send_json(
                500,
                {"ok": False, "error": "save_failed", "detail": str(exc)},
            )
            return
        self._send_json(200, {"ok": True})
        schedule_board_preview_capture(
            public_base_url=_board_preview_base_url(self),
            workspace_root=self.workspace_root,
            board_id=board_id,
        )

    def _post_api_sticker_board_registry(self) -> None:
        client_ip = self.client_address[0]
        if not client_may_write_sticker_board(client_ip):
            self._send_json(
                403,
                {
                    "ok": False,
                    "error": (
                        "Sticker board registry changes allowed from loopback only, "
                        "or set LENSES_ALLOW_GIT_ACTIONS=1"
                    ),
                },
            )
            return
        body = self._read_json_body(max_len=64_000)
        if not body:
            self._send_json(
                400,
                {"ok": False, "error": "invalid_json"},
            )
            return
        action = str(body.get("action", "")).strip().lower()
        payload = body.get("payload")
        if not isinstance(payload, dict):
            payload = {k: v for k, v in body.items() if k != "action"}
        state = self._scan(force_refresh=True)
        slugs = _child_slugs_from_scan(state)
        ok, err, extra = registry_apply(
            self.workspace_root,
            self.expected_github_login,
            slugs,
            action,
            payload,
        )
        if not ok:
            self._send_json(400, {"ok": False, "error": err})
            return
        self._send_json(200, {"ok": True, **(extra or {})})

    def _post_api_toolset_run(self) -> None:
        client_ip = self.client_address[0]
        if not client_may_run_git_actions(client_ip):
            self._send_json(
                403,
                {
                    "ok": False,
                    "error": (
                        "Toolset runs allowed from loopback only, "
                        "or set LENSES_ALLOW_GIT_ACTIONS=1"
                    ),
                    "stdout": "",
                    "stderr": "",
                    "exit_code": -1,
                },
            )
            return
        body = self._read_json_body()
        script = str(body.get("script", "")).strip()
        if not script:
            self._send_json(
                400,
                {
                    "ok": False,
                    "error": "missing_script",
                    "stdout": "",
                    "stderr": "",
                    "exit_code": -1,
                },
            )
            return
        result = run_toolset_script(self.workspace_root, script)
        payload = json.dumps(result, indent=2, sort_keys=True).encode("utf-8")
        if result.get("error") == "script_not_found_or_invalid":
            self._send(400, payload, "application/json; charset=utf-8")
            return
        code = 200 if result.get("ok") else 400
        self._send(code, payload, "application/json; charset=utf-8")


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
    parser.add_argument(
        "--bind-all-interfaces",
        action="store_true",
        help="Acknowledge binding to 0.0.0.0 / :: or a non-loopback IP (insecure on shared networks).",
    )
    args = parser.parse_args()

    import os

    env_root = os.environ.get("LENSES_WORKSPACE_ROOT")
    ws = resolve_workspace_root(LENSES_REPO_ROOT, args.workspace_root, env_root)
    registry = load_registry(LENSES_REPO_ROOT, ws)

    if _host_needs_bind_all_ack(args.host):
        if not args.bind_all_interfaces:
            print(
                "[lenses] ERROR: Non-loopback bind requires --bind-all-interfaces.\n"
                "[lenses] The dashboard and APIs are intended for 127.0.0.1 only.\n"
                "[lenses] Use: python3 -m lenses --host 127.0.0.1\n"
                "[lenses] Or pass --bind-all-interfaces if you accept the risk.",
                file=sys.stderr,
            )
            sys.exit(1)
        print(
            "[lenses] WARNING: Server is not loopback-only. "
            "Anyone who can reach this port may use the dashboard; "
            "privileged actions still require GitHub session + allowlist.",
            file=sys.stderr,
        )

    exp_login = resolve_expected_github_login(ws, registry)
    LensesHandler.workspace_root = ws
    LensesHandler.registry = registry
    LensesHandler.expected_github_login = exp_login
    LensesHandler.session_manager = SessionManager(ws)

    server = ThreadingHTTPServer((args.host, args.port), LensesHandler)
    print(f"[lenses] http://{args.host}:{args.port}/")
    print(f"[lenses] workspace_root={ws}")
    if exp_login:
        print(f"[lenses] expected_github_login={exp_login} (PAT must match for actions)")
    else:
        print(
            "[lenses] expected_github_login not set — allowlisted actions disabled until configured"
        )
    print(f"[lenses] docs static from {DOCS_DIR} (run generator/build-lenses-docs.py if empty)")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n[lenses] stopped")


if __name__ == "__main__":
    main()
