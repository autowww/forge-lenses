"""HTTP server: dynamic workspace UI, static /docs, JSON API."""

from __future__ import annotations

import argparse
import copy
import ipaddress
import json
import re
import mimetypes
import os
import sys
import threading
import time
import urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Literal, cast

from lenses.access_policy import (
    ROLE_DISCIPLINE_POWER,
    ROLE_MEMBER,
    ROLE_VIEWER,
    bootstrap_on_first_auth,
    can_manage_access,
    can_sign_in,
    is_policy_enforced,
    is_super_admin,
    listed_in_any_project,
    load_policy,
    power_user_may_assign_disciplines,
    remove_project_member,
    save_policy,
    set_project_member,
)
from lenses.auth_session import SESSION_COOKIE, SESSION_MAX_AGE_SEC, SessionManager, verify_github_token
from lenses.local_site_html import (
    build_local_site_base_href,
    content_type_for_local_site_file,
    inject_base_and_rewrite_local_site_html,
    local_site_directory_url_path,
)
from lenses.studio_embed_bridge import inject_studio_iframe_nav_bridge
from lenses.expected_github import resolve_expected_github_login
from lenses.board_preview import schedule_board_preview_capture
from lenses.chart_pages import page_overview_charts_api, page_project_charts_api
from lenses.git_actions import (
    client_may_run_git_actions,
    client_may_write_sticker_board,
    run_git_action,
)
from lenses.serve_rbac import (
    LOCAL_LOOPBACK_FACILITATOR_LOGIN,
    attach_git_identity,
    filter_sticker_registry_snapshot,
    project_access_bundle,
    resolve_facilitator_login,
    session_login as rbac_session_login,
)
from lenses.sticker_board import (
    MAX_BODY_BYTES as STICKER_BOARD_MAX_BODY_BYTES,
    UNASSIGNED_PROJECT_KEY,
    board_preview_path,
    can_edit_sticker_board,
    can_manage_board_acl,
    can_view_sticker_board,
    find_board_entry,
    is_valid_board_id,
    load_board,
    load_registry_raw,
    normalize_board,
    registry_apply,
    registry_entry_acl,
    registry_snapshot,
    save_board,
    share_add_guest_acl,
    stamp_guest_score_attribution,
    validate_board,
)
from lenses.sticker_board_share import (
    SHARE_SCOPE_COOKIE,
    build_public_url,
    is_valid_share_token,
    load_share,
    normalize_stickerboard_api_path,
    resolve_share_scope,
    share_join,
    share_metadata,
    share_revoke,
    share_scope_allows_path,
    share_public_config,
    share_start,
    stickerboard_loopback_dev_auth_enabled,
    stickerboard_port_allows_path,
)
from lenses.project_stats import collect_project_stats
from lenses.registry import load_registry
from lenses.forge_spine import build_plan_spine_payload, build_story_hub_payload
from lenses.roadmaps_matrix_api import build_roadmaps_matrix_payload
from lenses.today_charge_view import build_today_charge_payload
from lenses.workflow_context import build_workflow_context_payload
from lenses.forge_work_model import build_forge_work_model, work_model_selectors_payload
from lenses.render import (
    page_feature_showcase,
    page_overview,
    page_search,
    page_plan,
    page_timeline,
    page_project_detail,
    page_project_repo_strategy,
    page_projects,
    page_roadmap_preview_document,
    page_roadmap_timeline_document,
    page_view_embed,
    roadmap_summary_fragment,
    page_sticker_board_editor,
    page_sticker_board_hub,
    page_toolset,
    page_toolset_run,
    page_tutorials,
    page_wbs,
    page_wbs_view,
    page_workspace_md_view,
    page_websites,
    page_websites_browse,
    view_lenses_docs_href,
)
from lenses.roadmap_outline import (
    find_section,
    outline_json,
    parse_roadmap_markdown,
    section_to_html,
)
from lenses.safe_forge_paths import iter_workspace_md_index, safe_forge_workspace_file
from lenses.scan import (
    attach_fleet_test_attention,
    resolve_static_site_root,
    resolve_workspace_child_dir,
    resolve_workspace_root,
    scan_workspace,
    workspace_state_json,
)
from lenses.wbs_management import build_wbs_management_payload, create_wbs_md
from lenses.standards_compliance import enrich_workspace_with_standards
from lenses.timeline_api import build_timeline_api_payload
from lenses.tutorial_index import (
    build_tutorials_index_payload,
    repo_tutorials_url_tail_matches,
    resolve_repo_tutorials_site_file,
    resolve_tutorial_site_file,
    tutorial_url_tail_matches,
)
from lenses import llm_chat as llm_chat_api, search_db
from lenses.search_crawl import reindex_workspace
from lenses.shell_actions import client_may_run_shell_actions, run_allowlisted_action

# Browser dev servers (Vite); allow credentialed API calls when LENSES_ALLOW_DEV_CORS=1.
_DEV_CORS_ORIGINS = frozenset(
    {
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:4173",
        "http://127.0.0.1:4173",
    }
)
from lenses.toolset_actions import run_toolset_script


LENSES_REPO_ROOT = Path(__file__).resolve().parent.parent
DOCS_DIR = LENSES_REPO_ROOT / "lenses-docs"

# Default short TTL so repeated navigations reuse scan+standards work; override with LENSES_SCAN_CACHE_SEC.
_DEFAULT_SCAN_CACHE_SEC = 20.0
_scan_cache_lock = threading.Lock()
# Key: git_extended only (workspace is fixed per process). Value: (state dict, monotonic time).
_scan_cache_store: dict[tuple[bool], tuple[dict, float]] = {}

_search_reindex_lock = threading.Lock()
_search_reindex_status: dict[str, Any] = {
    "running": False,
    "last_error": None,
    "indexed": 0,
    "skipped": 0,
    "finished_at": None,
    "db_path": "",
}


def _safe_internal_redirect_path(raw: str) -> str | None:
    """Allow only same-origin path + query (e.g. ``/search`` or ``/search?q=…``)."""
    s = (raw or "").strip()
    if not s.startswith("/") or s.startswith("//"):
        return None
    if "\n" in s or "\r" in s or len(s) > 512:
        return None
    u = urllib.parse.urlparse(s)
    if u.scheme or u.netloc:
        return None
    if not u.path.startswith("/"):
        return None
    return s


def _merge_query_param(path: str, key: str, val: str) -> str:
    u = urllib.parse.urlparse(path)
    q = urllib.parse.parse_qs(u.query)
    q[key] = [val]
    return u.path + "?" + urllib.parse.urlencode(q, doseq=True)


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
    if candidate.name != "WBS.md":
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


def _iframe_src_for_view_docs(path_only: str) -> str:
    """Map ``/view/docs/…`` to raw ``/docs/…`` URL for iframe ``src``."""
    rest = path_only[len("/view/docs") :].lstrip("/")
    if not rest:
        return "/docs/index.html"
    return "/docs/" + rest


def _iframe_src_for_view_local_site(path_only: str) -> str | None:
    """Map ``/view/local-site/…`` to raw ``/local-site/…`` URL, or None if invalid."""
    rest = path_only[len("/view/local-site") :].lstrip("/")
    if not rest:
        return None
    return "/local-site/" + rest


def _docs_missing_html() -> bytes:
    return (
        "<!DOCTYPE html><html lang=\"en\"><head><meta charset=\"utf-8\"/>"
        "<meta name=\"viewport\" content=\"width=device-width, initial-scale=1\"/>"
        "<title>Not found — Lenses docs</title>"
        "<style>body{font-family:system-ui,sans-serif;margin:1.25rem;line-height:1.5;"
        "background:#0f172a;color:#e2e8f0;} a{color:#38bdf8;}</style></head><body>"
        "<p>This page is not in the built Lenses reference handbook.</p>"
        "<p><a href=\"/view/docs/index.html\">Reference home (in Lenses)</a> · "
        "<a href=\"/docs/index.html\">Raw doc URL</a> · "
        "<a href=\"/\">Lenses overview</a></p></body></html>"
    ).encode("utf-8")


def _local_site_missing_html() -> bytes:
    return (
        "<!DOCTYPE html><html lang=\"en\"><head><meta charset=\"utf-8\"/>"
        "<meta name=\"viewport\" content=\"width=device-width, initial-scale=1\"/>"
        "<title>Not found — preview</title>"
        "<style>body{font-family:system-ui,sans-serif;margin:1.25rem;line-height:1.5;"
        "background:#0f172a;color:#e2e8f0;} a{color:#38bdf8;}</style></head><body>"
        "<p>This file was not found under the workspace static preview path.</p>"
        "<p><a href=\"/tutorials\">Tutorials</a> · <a href=\"/websites\">Sites</a> · "
        "<a href=\"/\">Overview</a></p></body></html>"
    ).encode("utf-8")


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


def _safe_studio_static_file(lenses_repo_root: Path, url_path: str) -> Path | None:
    """Map ``/studio/…`` to ``lenses/static/studio/`` (Lenses Studio React shell)."""
    path_only = url_path.split("?", 1)[0]
    if path_only == "/studio":
        path_only = "/studio/"
    if not path_only.startswith("/studio/"):
        return None
    rest = path_only[len("/studio/") :].lstrip("/").replace("\\", "/")
    if not rest:
        rest = "index.html"
    if ".." in rest.split("/"):
        return None
    static_root = (lenses_repo_root / "lenses" / "static" / "studio").resolve()
    if not static_root.is_dir():
        return None
    candidate = (static_root / rest).resolve()
    try:
        candidate.relative_to(static_root)
    except ValueError:
        return None
    if not candidate.is_file():
        return None
    return candidate


_STUDIO_STATIC_SUFFIXES = frozenset(
    {
        ".css",
        ".js",
        ".map",
        ".json",
        ".woff",
        ".woff2",
        ".ttf",
        ".png",
        ".jpg",
        ".jpeg",
        ".gif",
        ".webp",
        ".svg",
        ".ico",
        ".webmanifest",
    }
)


def _studio_spa_index_fallback(lenses_repo_root: Path, url_path: str) -> Path | None:
    """When no file exists for ``/studio/…``, serve ``index.html`` for client-side routing.

    Missing hashed assets (``.js``, ``.css``, …) return ``None`` so the caller can **404**.
    """
    path_only = url_path.split("?", 1)[0]
    if path_only == "/studio":
        return None
    if not path_only.startswith("/studio/"):
        return None
    rest = path_only[len("/studio/") :].lstrip("/").replace("\\", "/")
    if ".." in rest.split("/"):
        return None
    static_root = (lenses_repo_root / "lenses" / "static" / "studio").resolve()
    if not static_root.is_dir():
        return None
    if not rest:
        return None
    candidate = (static_root / rest).resolve()
    try:
        candidate.relative_to(static_root)
    except ValueError:
        return None
    if candidate.is_file():
        return None
    suf = candidate.suffix.lower()
    if suf in _STUDIO_STATIC_SUFFIXES:
        return None
    index_html = (static_root / "index.html").resolve()
    try:
        index_html.relative_to(static_root)
    except ValueError:
        return None
    if index_html.is_file():
        return index_html
    return None


def _stickerboard_static_root(lenses_repo_root: Path) -> Path | None:
    static_root = (lenses_repo_root / "lenses" / "static" / "stickerboard").resolve()
    return static_root if static_root.is_dir() else None


def _safe_stickerboard_static_at_root(lenses_repo_root: Path, url_path: str) -> Path | None:
    """Map ``/`` and ``/assets/…`` to ``lenses/static/stickerboard/`` (local :9999)."""
    static_root = _stickerboard_static_root(lenses_repo_root)
    if static_root is None:
        return None
    path_only = url_path.split("?", 1)[0]
    if path_only in ("", "/"):
        for name in ("index.html", "stickerboard-index.html"):
            candidate = (static_root / name).resolve()
            try:
                candidate.relative_to(static_root)
            except ValueError:
                continue
            if candidate.is_file():
                return candidate
        return None
    rest = path_only.lstrip("/").replace("\\", "/")
    if not rest or ".." in rest.split("/"):
        return None
    if rest.startswith("api/") or rest.startswith("studio"):
        return None
    candidate = (static_root / rest).resolve()
    try:
        candidate.relative_to(static_root)
    except ValueError:
        return None
    if candidate.is_file():
        return candidate
    return None


def _stickerboard_spa_fallback_at_root(lenses_repo_root: Path, url_path: str) -> Path | None:
    """SPA fallback for ``/<shareToken>`` on local :9999 (no ``/stickerboard`` prefix)."""
    static_root = _stickerboard_static_root(lenses_repo_root)
    if static_root is None:
        return None
    path_only = url_path.split("?", 1)[0].rstrip("/") or "/"
    if path_only.startswith("/api/") or path_only.startswith("/__ks/") or path_only.startswith(
        "/assets/"
    ):
        return None
    if path_only.startswith("/studio"):
        return None
    if path_only not in ("/",) and "/" in path_only.lstrip("/"):
        return None
    for index_name in ("index.html", "stickerboard-index.html"):
        index_html = (static_root / index_name).resolve()
        try:
            index_html.relative_to(static_root)
        except ValueError:
            continue
        if index_html.is_file():
            return index_html
    return None


def _read_stickerboard_static_file(path: Path) -> bytes:
    """Serve stickerboard HTML with relative ``./assets/`` (fixes blank page behind ``/stickerboard``)."""
    data = path.read_bytes()
    if path.suffix.lower() != ".html":
        return data
    text = data.decode("utf-8", errors="replace")
    if 'src="/assets/' in text or 'href="/assets/' in text:
        text = text.replace('src="/assets/', 'src="./assets/').replace(
            'href="/assets/', 'href="./assets/'
        )
        data = text.encode("utf-8")
    return data


def _safe_stickerboard_static_file(lenses_repo_root: Path, url_path: str) -> Path | None:
    """Map ``/stickerboard/…`` to ``lenses/static/stickerboard/`` (production proxy on :8080)."""
    path_only = url_path.split("?", 1)[0]
    if path_only == "/stickerboard":
        path_only = "/stickerboard/"
    if not path_only.startswith("/stickerboard/"):
        return None
    rest = path_only[len("/stickerboard/") :].lstrip("/").replace("\\", "/")
    if not rest:
        rest = "stickerboard-index.html"
    if ".." in rest.split("/"):
        return None
    static_root = (lenses_repo_root / "lenses" / "static" / "stickerboard").resolve()
    if not static_root.is_dir():
        return None
    candidate = (static_root / rest).resolve()
    try:
        candidate.relative_to(static_root)
    except ValueError:
        return None
    if not candidate.is_file():
        return None
    return candidate


def _stickerboard_spa_index_fallback(lenses_repo_root: Path, url_path: str) -> Path | None:
    path_only = url_path.split("?", 1)[0]
    if path_only == "/stickerboard":
        path_only = "/stickerboard/"
    if not path_only.startswith("/stickerboard/"):
        return None
    rest = path_only[len("/stickerboard/") :].lstrip("/").replace("\\", "/")
    if ".." in rest.split("/"):
        return None
    static_root = (lenses_repo_root / "lenses" / "static" / "stickerboard").resolve()
    if not static_root.is_dir():
        return None
    if not rest:
        return None
    candidate = (static_root / rest).resolve()
    try:
        candidate.relative_to(static_root)
    except ValueError:
        return None
    if candidate.is_file():
        return None
    suf = candidate.suffix.lower()
    if suf in _STUDIO_STATIC_SUFFIXES:
        return None
    for index_name in ("stickerboard-index.html", "index.html"):
        index_html = (static_root / index_name).resolve()
        try:
            index_html.relative_to(static_root)
        except ValueError:
            continue
        if index_html.is_file():
            return index_html
    return None


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
    """Built static files for ``/local-site/<name>/…`` (Firebase config optional)."""
    child = resolve_workspace_child_dir(workspace_root, site_name, registry)
    if child is None:
        return None
    return resolve_static_site_root(child)


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
    stickerboard_port_only: bool = False

    def log_message(self, fmt: str, *args: object) -> None:
        print(f"[lenses] {self.address_string()} - {fmt % args}")

    def _session_login(self) -> str | None:
        return rbac_session_login(self.session_manager, self.headers.get("Cookie"))

    def _session_profile(self) -> dict[str, str] | None:
        sm = self.session_manager
        if sm is None:
            return None
        sid = _cookie_value(self.headers.get("Cookie"), SESSION_COOKIE)
        return sm.session_profile(sid)

    def _share_scope(self) -> dict[str, str] | None:
        return resolve_share_scope(self.workspace_root, self.headers.get("Cookie"))

    def _stickerboard_port_only_active(self) -> bool:
        return bool(getattr(self, "stickerboard_port_only", False))

    def _route_access_blocked(self, path: str, method: str) -> bool:
        """Return True when a 401 was sent and the request must stop."""
        port_only = self._stickerboard_port_only_active()
        scope = self._share_scope()
        if port_only:
            if not stickerboard_port_allows_path(path, method):
                self._send_json(
                    401,
                    {"ok": False, "error": "stickerboard_port_forbidden"},
                )
                return True
            return False
        if scope and not port_only and not share_scope_allows_path(path, method):
            self._send_json(
                401,
                {"ok": False, "error": "share_scope_forbidden"},
            )
            return True
        if scope and path.rstrip("/") == "/api/sticker-board":
            qs = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query or "")
            bid = str(qs.get("board_id", [""])[0]).strip()
            if bid != scope.get("board_id"):
                self._send_json(
                    401,
                    {"ok": False, "error": "share_scope_board_mismatch"},
                )
                return True
        return False

    def _absolute_origin(self) -> str:
        from lenses.auth_oidc import public_request_origin

        return public_request_origin(
            host_header=self.headers.get("Host"),
            forwarded_proto=self.headers.get("X-Forwarded-Proto"),
            forwarded_host=self.headers.get("X-Forwarded-Host"),
        )

    def _project_access(self, project_slug: str) -> dict[str, Any]:
        b = project_access_bundle(
            self.workspace_root,
            self.registry,
            project_slug,
            self._session_login(),
        )
        attach_git_identity(b)
        return b

    def _send(self, code: int, body: bytes, content_type: str) -> None:
        self.send_response(code)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_file_stream_attachment(self, file_path: Path, download_filename: str) -> None:
        """Stream a file with ``Content-Disposition: attachment`` (chunked reads; suitable for large zips)."""
        try:
            size = file_path.stat().st_size
        except OSError:
            self.send_error(404)
            return
        self.send_response(200)
        self._apply_dev_cors_headers()
        self.send_header("Content-Type", "application/zip")
        self.send_header("Content-Length", str(size))
        safe_fn = download_filename.replace('"', "")
        self.send_header("Content-Disposition", f'attachment; filename="{safe_fn}"')
        self.end_headers()
        try:
            with open(file_path, "rb") as f:
                while True:
                    chunk = f.read(65536)
                    if not chunk:
                        break
                    self.wfile.write(chunk)
        except (BrokenPipeError, ConnectionResetError, OSError):
            pass

    def _apply_dev_cors_headers(self) -> None:
        if os.environ.get("LENSES_ALLOW_DEV_CORS", "").strip().lower() not in (
            "1",
            "true",
            "yes",
        ):
            return
        origin = (self.headers.get("Origin") or "").strip()
        if origin in _DEV_CORS_ORIGINS:
            self.send_header("Access-Control-Allow-Origin", origin)
            self.send_header("Access-Control-Allow-Credentials", "true")
            self.send_header("Vary", "Origin")

    def _send_json(
        self,
        code: int,
        obj: object,
        *,
        set_cookie: str | None = None,
    ) -> None:
        raw = json.dumps(obj, indent=2, sort_keys=True).encode("utf-8")
        self.send_response(code)
        self._apply_dev_cors_headers()
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
                        st = copy.deepcopy(state_cached)
                        attach_fleet_test_attention(self.workspace_root, st)
                        return st

        state = scan_workspace(
            self.workspace_root,
            LENSES_REPO_ROOT,
            self.registry,
            git_extended=git_extended,
        )
        enrich_on = os.environ.get("LENSES_STANDARDS_ENRICH", "1").strip().lower()
        if enrich_on not in ("0", "false", "no", "off"):
            enrich_workspace_with_standards(state, self.registry)
        attach_fleet_test_attention(self.workspace_root, state)
        if ttl is not None:
            with _scan_cache_lock:
                _scan_cache_store[key] = (state, time.monotonic())
        return copy.deepcopy(state)

    def _bump_scan_cache(self) -> None:
        with _scan_cache_lock:
            _scan_cache_store.clear()

    def do_OPTIONS(self) -> None:  # noqa: N802
        """CORS preflight for /api/* when using Vite against Lenses with LENSES_ALLOW_DEV_CORS=1."""
        parsed = urllib.parse.urlparse(self.path)
        p = parsed.path.rstrip("/") or "/"
        if not p.startswith("/api/"):
            self.send_response(404)
            self.end_headers()
            return
        if os.environ.get("LENSES_ALLOW_DEV_CORS", "").strip().lower() not in (
            "1",
            "true",
            "yes",
        ):
            self.send_response(404)
            self.end_headers()
            return
        origin = (self.headers.get("Origin") or "").strip()
        if origin not in _DEV_CORS_ORIGINS:
            self.send_response(403)
            self.end_headers()
            return
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", origin)
        self.send_header("Access-Control-Allow-Credentials", "true")
        self.send_header(
            "Access-Control-Allow-Methods",
            "GET, POST, PUT, DELETE, OPTIONS",
        )
        self.send_header(
            "Access-Control-Allow-Headers",
            "Content-Type, Accept, Cookie",
        )
        self.send_header("Access-Control-Max-Age", "86400")
        self.send_header("Vary", "Origin")
        self.end_headers()

    def do_GET(self) -> None:  # noqa: N802
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path.startswith("/stickerboard/api"):
            parsed = parsed._replace(path=normalize_stickerboard_api_path(parsed.path))
            self.path = parsed.path + (f"?{parsed.query}" if parsed.query else "")
        path_only_early = parsed.path.split("?", 1)[0]
        # Legacy React shell paths -> Lenses Studio
        if path_only_early == "/enterprise" or path_only_early.startswith("/enterprise/"):
            suffix = path_only_early[len("/enterprise") :]
            if suffix in ("", "/"):
                loc = "/studio/"
            else:
                loc = "/studio" + suffix
            if parsed.query:
                loc += "?" + parsed.query
            self.send_response(302)
            self.send_header("Location", loc)
            self.end_headers()
            return
        # So relative assets in /studio/index.html resolve correctly in the browser.
        if parsed.path == "/studio":
            self.send_response(302)
            self.send_header("Location", "/studio/")
            self.end_headers()
            return
        qs = urllib.parse.parse_qs(parsed.query or "")
        force_refresh = _refresh_query_truthy(qs)
        path = parsed.path.rstrip("/") or "/"
        if path != "/" and parsed.path.endswith("/") and not parsed.path.startswith("/docs"):
            path = parsed.path.rstrip("/") or "/"

        if self._route_access_blocked(path, "GET"):
            return

        if self._stickerboard_port_only_active():
            sb_root_file = _safe_stickerboard_static_at_root(LENSES_REPO_ROOT, parsed.path)
            if sb_root_file is not None:
                mime, _ = mimetypes.guess_type(str(sb_root_file))
                ctype = mime or "application/octet-stream"
                suf = sb_root_file.suffix.lower()
                if suf == ".css":
                    ctype = "text/css; charset=utf-8"
                elif suf == ".js":
                    ctype = "text/javascript; charset=utf-8"
                elif suf == ".html":
                    ctype = "text/html; charset=utf-8"
                data = _read_stickerboard_static_file(sb_root_file)
                self._send(200, data, ctype)
                return
            sb_root_fb = _stickerboard_spa_fallback_at_root(LENSES_REPO_ROOT, parsed.path)
            if sb_root_fb is not None:
                data = _read_stickerboard_static_file(sb_root_fb)
                self._send(200, data, "text/html; charset=utf-8")
                return
            sb_proxy_file = _safe_stickerboard_static_file(LENSES_REPO_ROOT, parsed.path)
            if sb_proxy_file is not None:
                mime, _ = mimetypes.guess_type(str(sb_proxy_file))
                ctype = mime or "application/octet-stream"
                suf = sb_proxy_file.suffix.lower()
                if suf == ".css":
                    ctype = "text/css; charset=utf-8"
                elif suf == ".js":
                    ctype = "text/javascript; charset=utf-8"
                elif suf == ".html":
                    ctype = "text/html; charset=utf-8"
                data = _read_stickerboard_static_file(sb_proxy_file)
                self._send(200, data, ctype)
                return
            sb_proxy_fb = _stickerboard_spa_index_fallback(LENSES_REPO_ROOT, parsed.path)
            if sb_proxy_fb is not None:
                data = _read_stickerboard_static_file(sb_proxy_fb)
                self._send(200, data, "text/html; charset=utf-8")
                return

        eu = self.registry.get("external_urls") or {}
        handbook_url = str(eu.get("handbook", "https://blueprints.forgesdlc.com/"))
        forge_url = str(eu.get("forge", "https://forgesdlc.com/"))

        if path == "/api/llm/providers":
            client_ip = self.client_address[0]
            if not client_may_run_shell_actions(client_ip):
                self._send_json(
                    403,
                    {"ok": False, "error": "llm_api_allowed_from_loopback_or_lenses_allow_actions"},
                )
                return
            self._send_json(
                200,
                {
                    "ok": True,
                    "providers": llm_chat_api.providers_available(self.workspace_root),
                },
            )
            return

        if path == "/api/sdlc-copilot/enabled":
            client_ip = self.client_address[0]
            if not client_may_run_shell_actions(client_ip):
                self._send_json(
                    403,
                    {"ok": False, "error": "llm_api_allowed_from_loopback_or_lenses_allow_actions"},
                )
                return
            from lenses.sdlc_copilot.feature_flag import experimental_sdlc_copilot_enabled

            self._send_json(
                200,
                {"ok": True, "enabled": experimental_sdlc_copilot_enabled()},
            )
            return

        if path == "/api/sdlc-copilot/chat-stream":
            client_ip = self.client_address[0]
            if not client_may_run_shell_actions(client_ip):
                self._send_json(
                    403,
                    {"ok": False, "error": "llm_api_allowed_from_loopback_or_lenses_allow_actions"},
                )
                return
            sid = str(qs.get("session_id", [""])[0] or "").strip()
            if not sid:
                self._send_json(400, {"ok": False, "error": "missing_session_id"})
                return
            from lenses.sdlc_copilot.copilot_async_session import load_session, write_copilot_chat_sse

            if load_session(self.workspace_root, sid) is None:
                self._send_json(404, {"ok": False, "error": "session_not_found"})
                return
            write_copilot_chat_sse(self, self.workspace_root, sid)
            return

        if path == "/api/llm/settings":
            client_ip = self.client_address[0]
            if not client_may_run_shell_actions(client_ip):
                self._send_json(
                    403,
                    {"ok": False, "error": "llm_api_allowed_from_loopback_or_lenses_allow_actions"},
                )
                return
            from lenses.llm_settings_store import load_raw, sanitize_for_get

            data = load_raw(self.workspace_root)
            self._send_json(200, {"ok": True, "settings": sanitize_for_get(data)})
            return

        if path == "/api/llm/usage":
            client_ip = self.client_address[0]
            if not client_may_run_shell_actions(client_ip):
                self._send_json(
                    403,
                    {"ok": False, "error": "llm_api_allowed_from_loopback_or_lenses_allow_actions"},
                )
                return
            from lenses.llm_usage_store import get_usage_summary

            self._send_json(
                200,
                {"ok": True, "usage": get_usage_summary(self.workspace_root)},
            )
            return

        if path == "/api/llm/diagnostics":
            client_ip = self.client_address[0]
            if not client_may_run_shell_actions(client_ip):
                self._send_json(
                    403,
                    {"ok": False, "error": "llm_api_allowed_from_loopback_or_lenses_allow_actions"},
                )
                return
            from lenses.llm_diagnostics import build_llm_diagnostics

            self._send_json(200, build_llm_diagnostics(self.workspace_root))
            return

        if path == "/api/fleet/settings":
            client_ip = self.client_address[0]
            if not client_may_run_shell_actions(client_ip):
                self._send_json(
                    403,
                    {"ok": False, "error": "llm_api_allowed_from_loopback_or_lenses_allow_actions"},
                )
                return
            from lenses.fleet_settings_store import load_raw, sanitize_for_get

            data = load_raw(self.workspace_root)
            self._send_json(200, {"ok": True, "settings": sanitize_for_get(data)})
            return

        if path == "/api/llm/ollama-status":
            client_ip = self.client_address[0]
            if not client_may_run_shell_actions(client_ip):
                self._send_json(
                    403,
                    {"ok": False, "error": "llm_api_allowed_from_loopback_or_lenses_allow_actions"},
                )
                return
            st = llm_chat_api.ollama_daemon_status()
            from lenses.llm_usage_store import ollama_model_last_used_iso

            last_map = ollama_model_last_used_iso(self.workspace_root)
            catalog = st.get("model_catalog")
            if isinstance(catalog, list):
                for row in catalog:
                    if not isinstance(row, dict):
                        continue
                    name = str(row.get("name") or "").strip()
                    if not name:
                        row["last_used"] = None
                        continue
                    lu = last_map.get(name)
                    if not lu:
                        base = name.split(":", 1)[0].strip()
                        if base:
                            lu = last_map.get(base)
                    row["last_used"] = lu if lu else None
            self._send_json(200, {"ok": True, **st})
            return

        if path == "/api/llm/model-catalog-notifications":
            client_ip = self.client_address[0]
            if not client_may_run_shell_actions(client_ip):
                self._send_json(
                    403,
                    {"ok": False, "error": "llm_api_allowed_from_loopback_or_lenses_allow_actions"},
                )
                return
            from lenses.llm_model_catalog_snapshot import refresh_catalog_notifications

            self._send_json(200, refresh_catalog_notifications(self.workspace_root))
            return

        if path == "/api/llm/routing-preview":
            client_ip = self.client_address[0]
            if not client_may_run_shell_actions(client_ip):
                self._send_json(
                    403,
                    {"ok": False, "error": "llm_api_allowed_from_loopback_or_lenses_allow_actions"},
                )
                return
            from lenses.llm_resolve import build_routing_preview

            self._send_json(200, build_routing_preview(self.workspace_root))
            return

        if path.startswith("/api/agent-runtime"):
            client_ip = self.client_address[0]
            if not client_may_run_shell_actions(client_ip):
                self._send_json(
                    403,
                    {
                        "ok": False,
                        "error": "agent_runtime_api_allowed_from_loopback_or_lenses_allow_actions",
                    },
                )
                return
            if path.endswith("/stream"):
                from lenses.agent_runtime.http import parse_stream_session_id, write_session_sse

                sid = parse_stream_session_id(path)
                if not sid:
                    self._send_json(400, {"ok": False, "error": "bad_stream_path"})
                    return
                write_session_sse(self, self.workspace_root, sid)
                return
            from lenses.agent_runtime.http import handle_agent_runtime_get

            if handle_agent_runtime_get(self.workspace_root, path, parsed, send_json=self._send_json):
                return

        if path == "/api/blueprints/wizard/enabled":
            from lenses.blueprints_wizard.feature_flag import experimental_blueprints_wizard_enabled

            self._send_json(
                200,
                {"ok": True, "enabled": experimental_blueprints_wizard_enabled()},
            )
            return

        if path == "/api/delivery/enabled":
            from lenses.delivery_signals.feature_flag import experimental_delivery_signals_enabled

            self._send_json(
                200,
                {"ok": True, "enabled": experimental_delivery_signals_enabled()},
            )
            return

        if path == "/api/delivery/overview":
            from lenses.delivery_signals import build_delivery_overview_payload

            state = self._scan(git_extended=True, force_refresh=force_refresh)
            payload = build_delivery_overview_payload(
                workspace_root=self.workspace_root,
                scan_state=state,
            )
            self._send_json(200, payload)
            return

        if path == "/api/repo-workflow/enabled":
            from lenses.repo_workflow.feature_flag import experimental_repo_workflow_enabled

            self._send_json(200, {"ok": True, "enabled": experimental_repo_workflow_enabled()})
            return

        if path == "/api/repo-workflow/overview":
            from lenses.repo_workflow import build_repo_workflow_overview_payload

            state = self._scan(git_extended=True, force_refresh=force_refresh)
            payload = build_repo_workflow_overview_payload(
                workspace_root=self.workspace_root,
                scan_state=state,
            )
            self._send_json(200, payload)
            return

        if path == "/api/cicd/enabled":
            from lenses.cicd_orchestration.feature_flag import experimental_cicd_orchestration_enabled

            self._send_json(200, {"ok": True, "enabled": experimental_cicd_orchestration_enabled()})
            return

        if path == "/api/cicd/control-tower":
            from lenses.cicd_orchestration import build_cicd_control_tower_payload

            state = self._scan(git_extended=True, force_refresh=force_refresh)
            payload = build_cicd_control_tower_payload(
                workspace_root=self.workspace_root,
                scan_state=state,
            )
            self._send_json(200, payload)
            return

        if path == "/api/quality/enabled":
            from lenses.test_quality.feature_flag import experimental_test_quality_enabled

            self._send_json(200, {"ok": True, "enabled": experimental_test_quality_enabled()})
            return

        if path == "/api/quality/overview":
            from lenses.test_quality import build_quality_overview_payload

            state = self._scan(git_extended=True, force_refresh=force_refresh)
            payload = build_quality_overview_payload(
                workspace_root=self.workspace_root,
                scan_state=state,
            )
            self._send_json(200, payload)
            return

        if path == "/api/devsecops/enabled":
            from lenses.devsecops_compliance.feature_flag import experimental_devsecops_compliance_enabled

            self._send_json(200, {"ok": True, "enabled": experimental_devsecops_compliance_enabled()})
            return

        if path == "/api/devsecops/overview":
            from lenses.devsecops_compliance import build_devsecops_overview_payload

            state = self._scan(git_extended=True, force_refresh=force_refresh)
            payload = build_devsecops_overview_payload(
                workspace_root=self.workspace_root,
                scan_state=state,
            )
            self._send_json(200, payload)
            return

        if path == "/api/cross-team-release/enabled":
            from lenses.cross_team_release.feature_flag import experimental_cross_team_release_enabled

            self._send_json(200, {"ok": True, "enabled": experimental_cross_team_release_enabled()})
            return

        if path == "/api/cross-team-release/overview":
            from lenses.cross_team_release import build_cross_team_release_overview

            state = self._scan(git_extended=True, force_refresh=force_refresh)
            payload = build_cross_team_release_overview(
                workspace_root=self.workspace_root,
                scan_state=state,
            )
            self._send_json(200, payload)
            return

        if path == "/api/ops-delivery/enabled":
            from lenses.ops_delivery.feature_flag import experimental_ops_delivery_enabled

            self._send_json(200, {"ok": True, "enabled": experimental_ops_delivery_enabled()})
            return

        if path == "/api/ops-delivery/overview":
            from lenses.ops_delivery import build_ops_delivery_overview

            state = self._scan(git_extended=True, force_refresh=force_refresh)
            payload = build_ops_delivery_overview(
                workspace_root=self.workspace_root,
                scan_state=state,
            )
            self._send_json(200, payload)
            return

        if path == "/api/orchestration/enabled":
            from lenses.orchestration_graph.feature_flag import experimental_orchestration_graph_enabled

            self._send_json(
                200,
                {"ok": True, "enabled": experimental_orchestration_graph_enabled()},
            )
            return

        if path == "/api/orchestration/status":
            from lenses.orchestration_graph.db import connect, graph_stats
            from lenses.orchestration_graph.feature_flag import experimental_orchestration_graph_enabled

            if not experimental_orchestration_graph_enabled():
                self._send_json(
                    200,
                    {"ok": False, "feature_disabled": True},
                )
                return
            conn = connect(self.workspace_root)
            if conn is None:
                self._send_json(
                    200,
                    {"ok": False, "feature_disabled": True},
                )
                return
            try:
                st = graph_stats(conn)
                self._send_json(200, {"ok": True, "feature_disabled": False, **st})
            finally:
                conn.close()
            return

        if path == "/api/orchestration/entity":
            from lenses.orchestration_graph.db import connect
            from lenses.orchestration_graph.feature_flag import experimental_orchestration_graph_enabled
            from lenses.orchestration_graph.query import fetch_entity

            if not experimental_orchestration_graph_enabled():
                self._send_json(
                    200,
                    {"ok": False, "feature_disabled": True},
                )
                return
            eqs = urllib.parse.parse_qs(parsed.query or "")
            ids = eqs.get("id", [])
            eid = str(ids[0]).strip() if ids else ""
            if not eid:
                self._send_json(400, {"ok": False, "error": "missing_id"})
                return
            conn = connect(self.workspace_root)
            if conn is None:
                self._send_json(503, {"ok": False, "error": "graph_unavailable"})
                return
            try:
                ent = fetch_entity(conn, eid)
                if ent is None:
                    self._send_json(
                        404,
                        {"ok": False, "error": "entity_not_found", "id": eid},
                    )
                    return
                self._send_json(200, {"ok": True, "entity": ent})
            finally:
                conn.close()
            return

        if path == "/api/orchestration/trace":
            from lenses.orchestration_graph.db import connect
            from lenses.orchestration_graph.feature_flag import experimental_orchestration_graph_enabled
            from lenses.orchestration_graph.query import trace_subgraph

            if not experimental_orchestration_graph_enabled():
                self._send_json(
                    200,
                    {"ok": False, "feature_disabled": True, "nodes": [], "edges": []},
                )
                return
            tqs = urllib.parse.parse_qs(parsed.query or "")
            roots = tqs.get("root", [])
            root_id = str(roots[0]).strip() if roots else ""
            if not root_id:
                self._send_json(400, {"ok": False, "error": "missing_root"})
                return
            direction_raw = str(tqs.get("direction", ["both"])[0] or "both").lower()
            direction = direction_raw if direction_raw in ("out", "in", "both") else "both"
            try:
                max_depth = int(str(tqs.get("max_depth", ["5"])[0] or "5"))
            except ValueError:
                max_depth = 5
            try:
                max_nodes = int(str(tqs.get("max_nodes", ["400"])[0] or "400"))
            except ValueError:
                max_nodes = 400
            conn = connect(self.workspace_root)
            if conn is None:
                self._send_json(
                    503,
                    {"ok": False, "error": "graph_unavailable"},
                )
                return
            try:
                payload = trace_subgraph(
                    conn,
                    root_id,
                    direction=cast(Literal["out", "in", "both"], direction),
                    max_depth=max_depth,
                    max_nodes=max_nodes,
                )
                self._send_json(200, payload)
            finally:
                conn.close()
            return

        if (
            path.startswith("/api/artifacts")
            or path.startswith("/api/decisions")
            or path.startswith("/api/review-packs")
            or path.startswith("/api/assay-packets")
            or path.startswith("/api/evidence/")
            or path.startswith("/api/methodology/")
        ):
            from lenses.bridge.methodology_http import handle_methodology_b2_get

            if handle_methodology_b2_get(
                workspace_root=self.workspace_root,
                path=path,
                parsed=parsed,
                send_json=self._send_json,
            ):
                return

        if path.startswith("/api/agents"):
            from lenses.bridge.agentic_http import handle_agentic_b3_get

            if handle_agentic_b3_get(
                workspace_root=self.workspace_root,
                path=path,
                parsed=parsed,
                send_json=self._send_json,
            ):
                return

        if path.startswith("/api/ceremonies"):
            from lenses.bridge.ceremony_http import handle_ceremony_b4_get

            if handle_ceremony_b4_get(
                workspace_root=self.workspace_root,
                path=path,
                parsed=parsed,
                send_json=self._send_json,
            ):
                return

        if path.startswith("/api/handoffs") or path.startswith("/api/execution-sessions"):
            from lenses.bridge.handoff_http import handle_handoff_b5_get

            if handle_handoff_b5_get(
                workspace_root=self.workspace_root,
                path=path,
                parsed=parsed,
                send_json=self._send_json,
            ):
                return

        if path.startswith("/api/outcomes") or path.startswith("/api/launches") or path.startswith(
            "/api/pdlc/bridge"
        ):
            from lenses.bridge.outcome_http import handle_outcome_b6_get

            if handle_outcome_b6_get(
                workspace_root=self.workspace_root,
                path=path,
                parsed=parsed,
                send_json=self._send_json,
            ):
                return

        if path.startswith("/api/bridge/"):
            from lenses.bridge.api_handlers import handle_bridge_get

            if handle_bridge_get(
                workspace_root=self.workspace_root,
                path=path,
                parsed=parsed,
                send_json=self._send_json,
            ):
                return

        if path == "/api/orchestration/portfolio-context":
            from lenses.orchestration_graph.db import connect
            from lenses.orchestration_graph.feature_flag import experimental_orchestration_graph_enabled
            from lenses.orchestration_graph.portfolio import portfolio_context_payload

            if not experimental_orchestration_graph_enabled():
                self._send_json(200, {"ok": False, "feature_disabled": True})
                return
            pqs = urllib.parse.parse_qs(parsed.query or "")
            sa = str(pqs.get("scenario_a", [""])[0] or "").strip()
            sb = str(pqs.get("scenario_b", [""])[0] or "").strip()
            slip = str(pqs.get("slip_focus", [""])[0] or "").strip()
            conn = connect(self.workspace_root)
            if conn is None:
                self._send_json(503, {"ok": False, "error": "graph_unavailable"})
                return
            try:
                out = portfolio_context_payload(
                    conn,
                    scenario_a=sa or None,
                    scenario_b=sb or None,
                    slip_focus_id=slip or None,
                )
                self._send_json(200, out)
            finally:
                conn.close()
            return

        if path == "/api/blueprints/wizard/sessions":
            from lenses.blueprints_wizard.api import get_sessions_list
            from lenses.blueprints_wizard.feature_flag import experimental_blueprints_wizard_enabled

            if not experimental_blueprints_wizard_enabled():
                self._send_json(404, {"ok": False, "error": "feature_disabled"})
                return
            out = get_sessions_list(self.workspace_root)
            self._send_json(200, out)
            return

        if path.startswith("/api/blueprints/wizard/session/"):
            from lenses.blueprints_wizard.api import (
                get_session,
                parse_session_cursor_launch_pack_download_path,
                parse_session_path,
                parse_session_refine_path,
            )
            from lenses.blueprints_wizard.feature_flag import experimental_blueprints_wizard_enabled
            from lenses.blueprints_wizard.launch_pack_staging import (
                cleanup_expired_staged_zips,
                consume_staged_zip,
                staged_zip_path,
            )

            if not experimental_blueprints_wizard_enabled():
                self._send_json(404, {"ok": False, "error": "feature_disabled"})
                return
            dl_parts = parse_session_cursor_launch_pack_download_path(path)
            if dl_parts is not None:
                sid_dl, token = dl_parts
                client_ip = self.client_address[0]
                if not client_may_run_shell_actions(client_ip):
                    self._send_json(
                        403,
                        {
                            "ok": False,
                            "error": "llm_chat_allowed_from_loopback_or_lenses_allow_actions",
                        },
                    )
                    return
                cleanup_expired_staged_zips(self.workspace_root)
                zp = staged_zip_path(self.workspace_root, sid_dl, token)
                if zp is None:
                    self._send_json(404, {"ok": False, "error": "not_found"})
                    return
                fn = f"cursor-launch-pack-{sid_dl[:16]}.zip"
                self._send_file_stream_attachment(zp, fn)
                consume_staged_zip(zp)
                return
            if parse_session_refine_path(path) is not None:
                self._send_json(
                    405,
                    {"ok": False, "error": "method_not_allowed", "detail": "Use POST for refine."},
                )
                return
            sid = parse_session_path(path)
            if sid is None:
                self._send_json(400, {"ok": False, "error": "invalid_session_id"})
                return
            out = get_session(self.workspace_root, sid)
            if not out.get("ok"):
                err = str(out.get("error", ""))
                if err == "not_found":
                    self._send_json(404, out)
                else:
                    self._send_json(400, out)
                return
            self._send_json(200, out)
            return

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

        studio_file = _safe_studio_static_file(LENSES_REPO_ROOT, parsed.path)
        if studio_file is not None:
            mime, _ = mimetypes.guess_type(str(studio_file))
            ctype = mime or "application/octet-stream"
            suf = studio_file.suffix.lower()
            if suf == ".css":
                ctype = "text/css; charset=utf-8"
            elif suf == ".js":
                ctype = "text/javascript; charset=utf-8"
            elif suf == ".html":
                ctype = "text/html; charset=utf-8"
            elif suf == ".svg":
                ctype = "image/svg+xml; charset=utf-8"
            data = studio_file.read_bytes()
            self._send(200, data, ctype)
            return

        studio_fallback = _studio_spa_index_fallback(LENSES_REPO_ROOT, parsed.path)
        if studio_fallback is not None:
            data = studio_fallback.read_bytes()
            self._send(200, data, "text/html; charset=utf-8")
            return

        if not self._stickerboard_port_only_active():
            stickerboard_file = _safe_stickerboard_static_file(LENSES_REPO_ROOT, parsed.path)
        else:
            stickerboard_file = None
        if stickerboard_file is not None:
            mime, _ = mimetypes.guess_type(str(stickerboard_file))
            ctype = mime or "application/octet-stream"
            suf = stickerboard_file.suffix.lower()
            if suf == ".css":
                ctype = "text/css; charset=utf-8"
            elif suf == ".js":
                ctype = "text/javascript; charset=utf-8"
            elif suf == ".html":
                ctype = "text/html; charset=utf-8"
            elif suf == ".svg":
                ctype = "image/svg+xml; charset=utf-8"
            data = _read_stickerboard_static_file(stickerboard_file)
            self._send(200, data, ctype)
            return

        if not self._stickerboard_port_only_active():
            stickerboard_fallback = _stickerboard_spa_index_fallback(
                LENSES_REPO_ROOT, parsed.path
            )
        else:
            stickerboard_fallback = None
        if stickerboard_fallback is not None:
            data = _read_stickerboard_static_file(stickerboard_fallback)
            self._send(200, data, "text/html; charset=utf-8")
            return

        path_only_studio = parsed.path.split("?", 1)[0]
        if path_only_studio.startswith("/studio/"):
            rest_st = path_only_studio[len("/studio/") :].lstrip("/").replace("\\", "/")
            if rest_st and ".." not in rest_st.split("/"):
                static_st = (LENSES_REPO_ROOT / "lenses" / "static" / "studio").resolve()
                if static_st.is_dir():
                    cand_st = (static_st / rest_st).resolve()
                    try:
                        cand_st.relative_to(static_st)
                    except ValueError:
                        pass
                    else:
                        if (
                            not cand_st.is_file()
                            and cand_st.suffix.lower() in _STUDIO_STATIC_SUFFIXES
                        ):
                            self._send(
                                404,
                                b"Not found",
                                "text/plain; charset=utf-8",
                            )
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
            scope = self._share_scope()
            if scope:
                board_id = scope.get("board_id") or board_id
            if not is_valid_board_id(board_id):
                self._send_json(
                    400,
                    {"ok": False, "error": "missing_or_invalid_board_id"},
                )
                return
            board = load_board(
                self.workspace_root,
                self.expected_github_login,
                board_id,
                share_guest=bool(scope),
            )
            if board.get("board_not_found"):
                self._send_json(
                    404,
                    {"ok": False, "error": "board_not_found"},
                )
                return
            board.pop("board_not_found", None)
            from lenses.sticker_board import resolve_board_display_label

            reg = load_registry_raw(self.workspace_root)
            found = find_board_entry(reg, board_id)
            if scope:
                ent = found[1] if found else None
                board["board_label"] = resolve_board_display_label(
                    self.workspace_root,
                    board_id,
                    registry_entry=ent,
                    board_payload=board,
                )
                if found:
                    board["project"] = found[0]
                board["guest_role"] = scope.get("guest_role")
                raw = json.dumps(board, indent=2, sort_keys=True).encode("utf-8")
                self._send(200, raw, "application/json; charset=utf-8")
                return
            if found:
                proj_slug, ent = found
                bundle = self._project_access(proj_slug)
                is_sup = bool(bundle.get("is_workspace_super_admin"))
                cr = bool(bundle.get("can_read_project"))
                if not can_view_sticker_board(
                    self._session_login(),
                    ent,
                    is_workspace_super_admin=is_sup,
                    can_read_project=cr,
                ):
                    self._send_json(
                        403,
                        {"ok": False, "error": "sticker_board_forbidden"},
                    )
                    return
                board["board_acl"] = registry_entry_acl(ent)
                board["board_label"] = resolve_board_display_label(
                    self.workspace_root,
                    board_id,
                    registry_entry=ent,
                    board_payload=board,
                )
                board["project"] = proj_slug
            else:
                board["board_label"] = resolve_board_display_label(
                    self.workspace_root,
                    board_id,
                    board_payload=board,
                )
            raw = json.dumps(board, indent=2, sort_keys=True).encode("utf-8")
            self._send(200, raw, "application/json; charset=utf-8")
            return

        if path == "/api/sticker-board-share/config":
            self._send_json(200, share_public_config(self.workspace_root))
            return

        if path == "/api/sticker-board-share":
            self._get_api_sticker_board_share(parsed)
            return

        if path == "/api/sticker-board-registry":
            state = self._scan(force_refresh=force_refresh)
            slugs = _child_slugs_from_scan(state)
            snap = registry_snapshot(
                self.workspace_root, self.expected_github_login, slugs
            )
            snap = filter_sticker_registry_snapshot(
                snap,
                self.workspace_root,
                self.registry,
                self._session_login(),
            )
            snap["shared_login_configured"] = bool(self.expected_github_login)
            snap["workspace_projects"] = sorted(
                p for p in slugs if p != UNASSIGNED_PROJECT_KEY
            )
            raw = json.dumps(snap, indent=2, sort_keys=True).encode("utf-8")
            self._send(200, raw, "application/json; charset=utf-8")
            return

        if path == "/api/access/policy":
            policy = load_policy(self.workspace_root)
            sess = self._session_login()
            if not sess or not is_super_admin(policy, sess):
                self._send_json(
                    403,
                    {"ok": False, "error": "super_admin_required"},
                )
                return
            self._send_json(200, {"ok": True, "policy": policy})
            return

        if path == "/api/wbs-management":
            state = self._scan(force_refresh=force_refresh)
            payload = build_wbs_management_payload(
                self.workspace_root, self.registry, state
            )
            self._send_json(200, payload)
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

        if path == "/api/roadmap-section":
            rs_qs = urllib.parse.parse_qs(parsed.query or "")
            rs_rels = rs_qs.get("p", [])
            rs_secs = rs_qs.get("section", [])
            if not rs_rels or not rs_secs:
                self._send_json(
                    400, {"ok": False, "error": "missing_p_or_section"}
                )
                return
            rs_rel = str(rs_rels[0]).strip()
            rs_sec = str(rs_secs[0]).strip()
            rs_sp = _safe_roadmap_file(self.workspace_root, rs_rel)
            if rs_sp is None:
                self._send_json(404, {"ok": False, "error": "not_found"})
                return
            rs_text = rs_sp.read_text(encoding="utf-8", errors="replace")
            rs_parsed = parse_roadmap_markdown(rs_text)
            rs_found = find_section(rs_parsed, rs_sec)
            rs_html = (
                section_to_html(rs_found)
                if rs_found
                else "<p>Section not found.</p>"
            )
            self._send_json(
                200,
                {
                    "ok": True,
                    "html": rs_html,
                    "rel_path": rs_rel,
                    "section": rs_sec,
                },
            )
            return

        if path == "/api/roadmaps-matrix":
            qs = urllib.parse.parse_qs(parsed.query or "")
            repo_list = qs.get("repo", ["all"])
            repo_filter = str(repo_list[0]).strip() if repo_list else "all"
            state = self._scan(git_extended=False, force_refresh=force_refresh)
            payload = build_roadmaps_matrix_payload(
                self.workspace_root,
                state,
                repo_filter=repo_filter or "all",
            )
            if payload.get("ok"):
                from lenses.orchestration_graph.db import connect as _ogs_connect
                from lenses.orchestration_graph.feature_flag import (
                    experimental_orchestration_graph_enabled,
                )
                from lenses.orchestration_graph.portfolio import (
                    apply_milestone_graph_enrichment,
                    build_matrix_portfolio_overlay,
                )

                if experimental_orchestration_graph_enabled():
                    _ogc = _ogs_connect(self.workspace_root)
                    if _ogc is not None:
                        try:
                            apply_milestone_graph_enrichment(_ogc, payload)
                            payload["orchestration_portfolio"] = build_matrix_portfolio_overlay(
                                _ogc, payload
                            )
                        finally:
                            _ogc.close()
            self._send_json(200 if payload.get("ok") else 400, payload)
            return

        if path == "/api/plan-spine":
            qs = urllib.parse.parse_qs(parsed.query or "")
            wbs_list = qs.get("wbs_p", [])
            if not wbs_list or not str(wbs_list[0]).strip():
                self._send_json(400, {"ok": False, "error": "missing_wbs_p"})
                return
            wbs_rel = str(wbs_list[0]).strip()
            if _safe_wbs_file(self.workspace_root, wbs_rel) is None:
                self._send_json(404, {"ok": False, "error": "wbs_not_allowed"})
                return
            roadmap_list = qs.get("roadmap_p", [])
            roadmap_rel = str(roadmap_list[0]).strip() if roadmap_list else ""
            if roadmap_rel and _safe_roadmap_file(self.workspace_root, roadmap_rel) is None:
                self._send_json(404, {"ok": False, "error": "roadmap_not_allowed"})
                return
            repo_list = qs.get("repo", [])
            repo_hint = str(repo_list[0]).strip() if repo_list else ""
            payload = build_plan_spine_payload(
                self.workspace_root,
                repo_hint=repo_hint,
                wbs_rel=wbs_rel,
                roadmap_rel=roadmap_rel or None,
            )
            if payload.get("ok"):
                from lenses.orchestration_graph.db import connect as _ogs_connect2
                from lenses.orchestration_graph.feature_flag import (
                    experimental_orchestration_graph_enabled,
                )
                from lenses.orchestration_graph.portfolio import plan_spine_orchestration_summary

                if experimental_orchestration_graph_enabled():
                    _ogc2 = _ogs_connect2(self.workspace_root)
                    if _ogc2 is not None:
                        try:
                            payload["orchestration"] = plan_spine_orchestration_summary(_ogc2)
                        finally:
                            _ogc2.close()
            self._send_json(200 if payload.get("ok") else 404, payload)
            return

        if path == "/api/workflow-context":
            qs = urllib.parse.parse_qs(parsed.query or "")
            wbs_list = qs.get("wbs_p", [])
            if not wbs_list or not str(wbs_list[0]).strip():
                self._send_json(400, {"ok": False, "error": "missing_wbs_p"})
                return
            wbs_rel = str(wbs_list[0]).strip()
            if _safe_wbs_file(self.workspace_root, wbs_rel) is None:
                self._send_json(404, {"ok": False, "error": "wbs_not_allowed"})
                return
            roadmap_list = qs.get("roadmap_p", [])
            roadmap_rel = str(roadmap_list[0]).strip() if roadmap_list else ""
            if roadmap_rel and _safe_roadmap_file(self.workspace_root, roadmap_rel) is None:
                self._send_json(404, {"ok": False, "error": "roadmap_not_allowed"})
                return
            repo_list = qs.get("repo", [])
            repo_hint = str(repo_list[0]).strip() if repo_list else ""
            payload = build_workflow_context_payload(
                self.workspace_root,
                repo_hint=repo_hint,
                wbs_rel=wbs_rel,
                roadmap_rel=roadmap_rel or None,
            )
            self._send_json(200 if payload.get("ok") else 404, payload)
            return

        if path == "/api/today-charge":
            qs = urllib.parse.parse_qs(parsed.query or "")
            wbs_list = qs.get("wbs_p", [])
            if not wbs_list or not str(wbs_list[0]).strip():
                self._send_json(400, {"ok": False, "error": "missing_wbs_p"})
                return
            wbs_rel = str(wbs_list[0]).strip()
            if _safe_wbs_file(self.workspace_root, wbs_rel) is None:
                self._send_json(404, {"ok": False, "error": "wbs_not_allowed"})
                return
            roadmap_list = qs.get("roadmap_p", [])
            roadmap_rel = str(roadmap_list[0]).strip() if roadmap_list else ""
            if roadmap_rel and _safe_roadmap_file(self.workspace_root, roadmap_rel) is None:
                self._send_json(404, {"ok": False, "error": "roadmap_not_allowed"})
                return
            repo_list = qs.get("repo", [])
            repo_hint = str(repo_list[0]).strip() if repo_list else ""
            payload = build_today_charge_payload(
                self.workspace_root,
                repo_hint=repo_hint,
                wbs_rel=wbs_rel,
                roadmap_rel=roadmap_rel or None,
            )
            self._send_json(200 if payload.get("ok") else 404, payload)
            return

        if path == "/api/forge-work-model":
            qs = urllib.parse.parse_qs(parsed.query or "")
            wbs_list = qs.get("wbs_p", [])
            if not wbs_list or not str(wbs_list[0]).strip():
                self._send_json(400, {"ok": False, "error": "missing_wbs_p"})
                return
            wbs_rel = str(wbs_list[0]).strip()
            if _safe_wbs_file(self.workspace_root, wbs_rel) is None:
                self._send_json(404, {"ok": False, "error": "wbs_not_allowed"})
                return
            roadmap_list = qs.get("roadmap_p", [])
            roadmap_rel = str(roadmap_list[0]).strip() if roadmap_list else ""
            if roadmap_rel and _safe_roadmap_file(self.workspace_root, roadmap_rel) is None:
                self._send_json(404, {"ok": False, "error": "roadmap_not_allowed"})
                return
            repo_list = qs.get("repo", [])
            repo_hint = str(repo_list[0]).strip() if repo_list else ""
            model = build_forge_work_model(
                self.workspace_root,
                repo_hint=repo_hint,
                wbs_rel=wbs_rel,
                roadmap_rel=roadmap_rel or None,
            )
            node_ids = qs.get("node_id", [])
            node_id = str(node_ids[0]).strip() if node_ids else ""
            if node_id:
                payload = work_model_selectors_payload(model, node_id)
                self._send_json(200 if payload.get("ok") else 404, payload)
            else:
                blob = model.to_json_blob()
                self._send_json(200, {"ok": True, **blob})
            return

        if path == "/api/story-hub":
            qs = urllib.parse.parse_qs(parsed.query or "")
            ids = qs.get("id", [])
            if not ids or not str(ids[0]).strip():
                self._send_json(400, {"ok": False, "error": "missing_id"})
                return
            wid = str(ids[0]).strip()
            wbs_list = qs.get("wbs_p", [])
            if not wbs_list or not str(wbs_list[0]).strip():
                self._send_json(400, {"ok": False, "error": "missing_wbs_p"})
                return
            wbs_rel = str(wbs_list[0]).strip()
            if _safe_wbs_file(self.workspace_root, wbs_rel) is None:
                self._send_json(404, {"ok": False, "error": "wbs_not_allowed"})
                return
            roadmap_list = qs.get("roadmap_p", [])
            roadmap_rel = str(roadmap_list[0]).strip() if roadmap_list else ""
            if roadmap_rel and _safe_roadmap_file(self.workspace_root, roadmap_rel) is None:
                self._send_json(404, {"ok": False, "error": "roadmap_not_allowed"})
                return
            repo_list = qs.get("repo", [])
            repo_hint = str(repo_list[0]).strip() if repo_list else ""
            payload = build_story_hub_payload(
                self.workspace_root,
                repo_hint=repo_hint,
                wbs_rel=wbs_rel,
                work_item_id=wid,
                roadmap_rel=roadmap_rel or None,
            )
            self._send_json(200 if payload.get("ok") else 404, payload)
            return

        if path == "/api/workspace-state":
            ext = qs.get("git_extended", [])
            git_extended = bool(ext) and str(ext[0]).lower() in ("1", "true", "yes")
            state = self._scan(
                git_extended=git_extended, force_refresh=force_refresh
            )
            try:
                from lenses.kpi_history import append_kpi_snapshot

                append_kpi_snapshot(self.workspace_root, state)
            except Exception:
                pass
            raw = workspace_state_json(state).encode("utf-8")
            self._send(200, raw, "application/json; charset=utf-8")
            return

        if path == "/api/docs-health/summary":
            from lenses.docs_health.api_handlers import get_workspace_summary

            get_workspace_summary(self.workspace_root, self.registry, send_json=self._send_json)
            return

        if path == "/api/docs-health/work-items":
            from lenses.docs_health.api_handlers import get_workspace_work_items

            get_workspace_work_items(self.workspace_root, self.registry, send_json=self._send_json)
            return

        if path == "/api/docs-health/live-sessions":
            from lenses.docs_health.api_handlers import get_live_docs_sessions

            get_live_docs_sessions(self.workspace_root, self.registry, send_json=self._send_json)
            return

        if path == "/api/tutorials-index":
            state = self._scan(
                git_extended=False, force_refresh=force_refresh
            )
            payload = build_tutorials_index_payload(state)
            self._send_json(200, payload)
            return

        if path == "/api/forgesdlc-blog":
            from lenses.forgesdlc_blog import build_blog_payload

            payload = build_blog_payload(self.workspace_root)
            self._send_json(200, payload)
            return

        if path == "/api/forgesdlc-blog/content":
            from lenses.forgesdlc_blog import read_cached_html_with_base

            slug_qs = qs.get("slug", [])
            slug = str(slug_qs[0]).strip() if slug_qs else ""
            data, err = read_cached_html_with_base(self.workspace_root, slug)
            if err:
                self._send_json(
                    404,
                    {"ok": False, "error": err},
                )
                return
            self._send(200, data, "text/html; charset=utf-8")
            return

        if path == "/api/timeline-context":
            state = self._scan(git_extended=True, force_refresh=force_refresh)
            tqs = urllib.parse.parse_qs(parsed.query or "")
            from lenses.orchestration_graph.db import connect as _ogs_timeline
            from lenses.orchestration_graph.feature_flag import (
                experimental_orchestration_graph_enabled,
            )

            _og_timeline = None
            if experimental_orchestration_graph_enabled():
                _og_timeline = _ogs_timeline(self.workspace_root)
            try:
                payload = build_timeline_api_payload(
                    self.workspace_root,
                    state,
                    tqs,
                    orchestration_conn=_og_timeline,
                )
                self._send_json(200, payload)
            finally:
                if _og_timeline is not None:
                    _og_timeline.close()
            return

        if path == "/api/wbs-file":
            wf_qs = urllib.parse.parse_qs(parsed.query or "")
            wf_rels = wf_qs.get("p", [])
            if not wf_rels or not str(wf_rels[0]).strip():
                self._send_json(400, {"ok": False, "error": "missing_p"})
                return
            wf_rel = str(wf_rels[0]).strip()
            wf_sp = _safe_wbs_file(self.workspace_root, wf_rel)
            if wf_sp is None:
                self._send_json(404, {"ok": False, "error": "not_found"})
                return
            wf_text = wf_sp.read_text(encoding="utf-8", errors="replace")
            self._send_json(
                200,
                {
                    "ok": True,
                    "text": wf_text,
                    "kind": "md",
                    "rel_path": wf_rel,
                },
            )
            return

        if path == "/api/workspace-md-file":
            wm_qs = urllib.parse.parse_qs(parsed.query or "")
            wm_rels = wm_qs.get("p", [])
            if not wm_rels or not str(wm_rels[0]).strip():
                self._send_json(400, {"ok": False, "error": "missing_p"})
                return
            wm_rel = str(wm_rels[0]).strip()
            wm_sp = safe_forge_workspace_file(self.workspace_root, wm_rel)
            if wm_sp is None:
                self._send_json(404, {"ok": False, "error": "not_found"})
                return
            wm_text = wm_sp.read_text(encoding="utf-8", errors="replace")
            self._send_json(200, {"ok": True, "text": wm_text, "rel_path": wm_rel})
            return

        if path == "/api/workspace-md-index":
            files, truncated = iter_workspace_md_index(self.workspace_root, max_files=500)
            self._send_json(
                200,
                {"ok": True, "files": files, "truncated": truncated},
            )
            return

        if path == "/api/search":
            qv = qs.get("q", [])
            q = str(qv[0]).strip() if qv else ""
            lim_raw = qs.get("limit", [])
            off_raw = qs.get("offset", [])
            try:
                limit = int(str(lim_raw[0]).strip()) if lim_raw else 25
            except ValueError:
                limit = 25
            try:
                offset = int(str(off_raw[0]).strip()) if off_raw else 0
            except ValueError:
                offset = 0
            site_raw = qs.get("site", []) or qs.get("repo", [])
            scope_site = str(site_raw[0]).strip() if site_raw else ""
            if not q:
                self._send_json(
                    200,
                    {
                        "ok": True,
                        "hits": [],
                        "query": "",
                        "total": 0,
                        "limit": limit,
                        "offset": offset,
                    },
                )
                return
            conn = search_db.connect(self.workspace_root)
            try:
                result = search_db.search(
                    conn,
                    q,
                    limit=limit,
                    offset=offset,
                    scope_site=scope_site,
                )
            finally:
                conn.close()
            self._send_json(
                200,
                {
                    "ok": True,
                    "query": q,
                    "hits": result["hits"],
                    "total": result["total"],
                    "limit": result["limit"],
                    "offset": result["offset"],
                },
            )
            return

        if path == "/api/search/reindex":
            self._get_api_search_reindex(parsed)
            return

        if path == "/api/chart-data/overview":
            from lenses.chart_payloads import (
                build_overview_chart_payload,
                horizon_query_days,
                normalized_horizon_id,
            )

            hz_raw = qs.get("horizon", [])
            hz = str(hz_raw[0]).strip() if hz_raw else ""
            days = horizon_query_days(hz)
            hid = normalized_horizon_id(hz)
            state = self._scan(git_extended=True, force_refresh=force_refresh)
            self._send_json(
                200,
                build_overview_chart_payload(state, days=days, horizon_id=hid),
            )
            return

        if path == "/api/auth/status":
            from lenses.auth_oidc import load_oidc_config as _load_oidc

            sm = self.session_manager
            exp = self.expected_github_login
            sess_login = self._session_login()
            policy = load_policy(self.workspace_root)
            enforced = is_policy_enforced(policy)
            session_ok = bool(sess_login) and (
                not enforced
                or can_sign_in(policy, sess_login or "")
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
            is_sup = bool(sess_login and is_super_admin(policy, sess_login))
            sm = self.session_manager
            ck = _cookie_value(self.headers.get("Cookie"), SESSION_COOKIE)
            auth_provider = None
            if sm and ck:
                auth_provider = sm.session_auth_provider(ck)
            self._send_json(
                200,
                {
                    "expected_login": exp,
                    "expected_configured": bool(exp),
                    "session_login": sess_login,
                    "session_ok": session_ok,
                    "access_policy_enforced": enforced,
                    "workspace_super_admin": is_sup,
                    "auth_provider": auth_provider,
                    "oidc_configured": _load_oidc() is not None,
                    "stickerboard_loopback_dev_auth": stickerboard_loopback_dev_auth_enabled(),
                    "sites_with_allowlisted_actions": sites_with_actions,
                    "action_keys_by_site": action_keys_by_site,
                },
            )
            return

        if path == "/api/auth/oidc/status":
            from lenses.auth_oidc import oidc_status_payload

            payload = oidc_status_payload()
            payload["loopback_dev_auth"] = stickerboard_loopback_dev_auth_enabled()
            self._send_json(200, payload)
            return

        if path == "/api/auth/loopback-dev-login":
            self._send_json(405, {"ok": False, "error": "method_not_allowed"})
            return

        if path == "/api/auth/oidc/login":
            from lenses.auth_oidc import client_may_use_oidc_auth

            client_ip = self.client_address[0]
            if not client_may_use_oidc_auth(client_ip):
                self._send_json(
                    403,
                    {"ok": False, "error": "oidc_login_not_allowed"},
                )
                return
            from lenses.auth_oidc import load_oidc_config, start_authorize_url

            cfg = load_oidc_config()
            if not cfg:
                self._send_json(
                    503,
                    {"ok": False, "error": "oidc_not_configured"},
                )
                return
            redir = f"{self._absolute_origin()}{cfg.redirect_path}"
            qs_oidc = urllib.parse.parse_qs(parsed.query or "")
            return_to = str(qs_oidc.get("return_to", [""])[0]).strip()
            try:
                url, _state, _ver = start_authorize_url(
                    issuer=cfg.issuer,
                    client_id=cfg.client_id,
                    redirect_uri=redir,
                    scopes=cfg.scopes,
                    return_to=return_to or None,
                )
            except RuntimeError as ex:
                self._send_json(502, {"ok": False, "error": "oidc_start_failed", "detail": str(ex)})
                return
            self.send_response(302)
            self.send_header("Location", url)
            self.send_header("Content-Length", "0")
            self.end_headers()
            return

        if path == "/api/auth/oidc/callback":
            from lenses.auth_oidc import client_may_use_oidc_auth

            client_ip = self.client_address[0]
            if not client_may_use_oidc_auth(client_ip):
                self._send_json(403, {"ok": False, "error": "oidc_callback_not_allowed"})
                return
            from lenses.auth_oidc import (
                exchange_code_for_tokens,
                fetch_discovery,
                load_oidc_config,
                pop_verifier_for_state,
                resolve_oidc_login,
            )

            qs = urllib.parse.parse_qs(parsed.query or "")
            code = str(qs.get("code", [""])[0]).strip()
            state = str(qs.get("state", [""])[0]).strip()
            err_q = qs.get("error", [])
            if err_q:
                self._send_json(
                    400,
                    {
                        "ok": False,
                        "error": "oidc_provider_error",
                        "detail": str(err_q[0]),
                    },
                )
                return
            if not code or not state:
                self._send_json(400, {"ok": False, "error": "missing_code_or_state"})
                return
            verifier, return_to = pop_verifier_for_state(state)
            if not verifier:
                self._send_json(400, {"ok": False, "error": "invalid_or_expired_state"})
                return
            cfg = load_oidc_config()
            if not cfg:
                self._send_json(503, {"ok": False, "error": "oidc_not_configured"})
                return
            disc = fetch_discovery(cfg.issuer)
            if not disc:
                self._send_json(502, {"ok": False, "error": "oidc_discovery_failed"})
                return
            token_ep = str(disc.get("token_endpoint") or "").strip()
            userinfo_ep = str(disc.get("userinfo_endpoint") or "").strip() or None
            if not token_ep:
                self._send_json(502, {"ok": False, "error": "oidc_no_token_endpoint"})
                return
            redir = f"{self._absolute_origin()}{cfg.redirect_path}"
            tokens = exchange_code_for_tokens(
                issuer=cfg.issuer,
                token_endpoint=token_ep,
                client_id=cfg.client_id,
                client_secret=cfg.client_secret,
                redirect_uri=redir,
                code=code,
                code_verifier=verifier,
            )
            if not tokens:
                self._send_json(401, {"ok": False, "error": "oidc_token_exchange_failed"})
                return
            from lenses.auth_oidc import resolve_oidc_profile

            profile = resolve_oidc_profile(tokens, userinfo_ep)
            if not profile or not profile.get("login"):
                self._send_json(401, {"ok": False, "error": "oidc_no_subject"})
                return
            login = profile["login"]
            policy = bootstrap_on_first_auth(self.workspace_root, login)
            if not can_sign_in(policy, login):
                self._send_json(
                    403,
                    {"ok": False, "error": "access_denied_not_invited", "login": login},
                )
                return
            sm = self.session_manager
            if sm is None:
                self._send_json(500, {"ok": False, "error": "session_store_unavailable"})
                return
            sid = sm.create_session(
                login,
                auth_provider="oidc",
                display_name=profile.get("display_name"),
                email=profile.get("email"),
            )
            cookie = (
                f"{SESSION_COOKIE}={sid}; HttpOnly; SameSite=Lax; Path=/; "
                f"Max-Age={SESSION_MAX_AGE_SEC}"
            )
            loc = return_to if return_to else "/studio/"
            self.send_response(302)
            self.send_header("Location", loc)
            self.send_header("Set-Cookie", cookie)
            self.send_header("Content-Length", "0")
            self.end_headers()
            return

        if path == "/api/governance/scopes":
            policy = load_policy(self.workspace_root)
            sess = self._session_login()
            qs = urllib.parse.parse_qs(parsed.query or "")
            proj = str(qs.get("project", [""])[0]).strip() or None
            from lenses.governance.scopes import effective_scopes

            scopes, source = effective_scopes(policy, sess, proj)
            self._send_json(
                200,
                {
                    "ok": True,
                    "scopes": scopes,
                    "source": source,
                    "project": proj,
                },
            )
            return

        if path == "/api/governance/audit":
            policy = load_policy(self.workspace_root)
            sess = self._session_login()
            if not sess or not is_super_admin(policy, sess):
                self._send_json(403, {"ok": False, "error": "super_admin_required"})
                return
            qs = urllib.parse.parse_qs(parsed.query or "")
            try:
                lim = int(str(qs.get("limit", ["80"])[0]).strip())
            except ValueError:
                lim = 80
            from lenses.governance.audit_log import read_recent

            rows = read_recent(self.workspace_root, limit=lim)
            self._send_json(200, {"ok": True, "events": rows, "limit": lim})
            return

        if path == "/api/connectors/health":
            policy = load_policy(self.workspace_root)
            sess = self._session_login()
            if is_policy_enforced(policy) and not sess:
                self._send_json(403, {"ok": False, "error": "auth_required"})
                return
            if is_policy_enforced(policy) and sess:
                if not (
                    is_super_admin(policy, sess) or listed_in_any_project(policy, sess)
                ):
                    self._send_json(403, {"ok": False, "error": "forbidden"})
                    return
            state = self._scan(git_extended=False, force_refresh=force_refresh)
            from lenses.governance.connectors_health import build_connectors_health

            self._send_json(200, build_connectors_health(workspace_root=self.workspace_root, scan_state=state))
            return

        if parsed.path.startswith("/local-site/"):
            lp = _local_site_site_and_tail(parsed.path)
            if lp is None:
                self._send(404, _local_site_missing_html(), "text/html; charset=utf-8")
                return
            site_name, tail = lp
            sf = _safe_local_site_file(
                self.workspace_root, self.registry, site_name, tail
            )
            if sf is None:
                self._send(404, _local_site_missing_html(), "text/html; charset=utf-8")
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
                data = inject_studio_iframe_nav_bridge(data)
            self._send(200, data, ctype)
            return

        api_proj = _parse_api_project_subpath(parsed.path)
        if api_proj is not None:
            name, tail = api_proj
            if tail == "context":
                bundle = self._project_access(name)
                policy = bundle.get("policy") or {}
                sess = bundle.get("session_login")
                sess_s = str(sess).strip() if sess else None
                from lenses.governance.scopes import effective_scopes

                sc_list, sc_src = effective_scopes(policy, sess_s, name)
                self._send_json(
                    200,
                    {
                        "ok": True,
                        "project": name,
                        "role": bundle.get("role", ""),
                        "is_workspace_super_admin": bool(
                            bundle.get("is_workspace_super_admin")
                        ),
                        "can_read_project": bool(bundle.get("can_read_project")),
                        "can_write_project": bool(bundle.get("can_write_project")),
                        "effective_readonly": bool(bundle.get("effective_readonly")),
                        "access_policy_enforced": is_policy_enforced(policy),
                        "git_user_name": bundle.get("git_user_name", ""),
                        "git_user_email": bundle.get("git_user_email", ""),
                        "session_login": bundle.get("session_login"),
                        "scopes": sc_list,
                        "scopes_source": sc_src,
                    },
                )
                return
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
                bundle = self._project_access(name)
                if not bundle.get("can_read_project"):
                    self._send_json(
                        403,
                        {"ok": False, "error": "project_forbidden"},
                    )
                    return
                stats = collect_project_stats(child_path)
                raw = json.dumps(stats, indent=2, sort_keys=True).encode("utf-8")
                self._send(200, raw, "application/json; charset=utf-8")
                return
            if tail == "repo-workflow":
                from lenses.repo_workflow import build_project_repo_workflow_payload

                bundle = self._project_access(name)
                if not bundle.get("can_read_project"):
                    self._send_json(403, {"ok": False, "error": "project_forbidden"})
                    return
                state = self._scan(git_extended=True, force_refresh=force_refresh)
                payload = build_project_repo_workflow_payload(
                    workspace_root=self.workspace_root,
                    scan_state=state,
                    project_name=name,
                )
                self._send_json(200, payload)
                return
            if tail == "branching":
                from lenses.project_branching import build_project_branching_payload

                bundle = self._project_access(name)
                if not bundle.get("can_read_project"):
                    self._send_json(403, {"ok": False, "error": "project_forbidden"})
                    return
                child_path = resolve_workspace_child_dir(
                    self.workspace_root, name, self.registry
                )
                if child_path is None or not (child_path / ".git").exists():
                    self._send_json(404, {"ok": False, "error": "not_found"})
                    return
                state = self._scan(git_extended=True, force_refresh=force_refresh)
                payload = build_project_branching_payload(
                    workspace_root=self.workspace_root,
                    project_root=child_path,
                    project_name=name,
                    scan_state=state,
                )
                self._send_json(200, payload)
                return
            if tail == "quality":
                from lenses.test_quality import build_project_quality_payload

                bundle = self._project_access(name)
                if not bundle.get("can_read_project"):
                    self._send_json(403, {"ok": False, "error": "project_forbidden"})
                    return
                state = self._scan(git_extended=True, force_refresh=force_refresh)
                payload = build_project_quality_payload(
                    workspace_root=self.workspace_root,
                    scan_state=state,
                    project_name=name,
                )
                self._send_json(200, payload)
                return
            if tail == "devsecops":
                from lenses.devsecops_compliance import build_project_devsecops_payload

                bundle = self._project_access(name)
                if not bundle.get("can_read_project"):
                    self._send_json(403, {"ok": False, "error": "project_forbidden"})
                    return
                state = self._scan(git_extended=True, force_refresh=force_refresh)
                payload = build_project_devsecops_payload(
                    workspace_root=self.workspace_root,
                    scan_state=state,
                    project_name=name,
                )
                self._send_json(200, payload)
                return
            if tail == "chart-data":
                from lenses.chart_payloads import build_project_chart_payload

                child_path = resolve_workspace_child_dir(
                    self.workspace_root, name, self.registry
                )
                if child_path is None or not (child_path / ".git").exists():
                    self._send_json(404, {"error": "not_found"})
                    return
                bundle = self._project_access(name)
                if not bundle.get("can_read_project"):
                    self._send_json(
                        403,
                        {"ok": False, "error": "project_forbidden"},
                    )
                    return
                state = self._scan(
                    git_extended=True, force_refresh=force_refresh
                )
                payload = build_project_chart_payload(child_path, state, name)
                self._send_json(200, payload)
                return
            if tail == "docs-health-session-events":
                from lenses.docs_health.feature_flag import docs_health_enabled
                from lenses.docs_health.run_projection import merge_docs_health_session_view

                if not docs_health_enabled():
                    self._send_json(404, {"ok": False, "error": "feature_disabled"})
                    return
                qs = urllib.parse.parse_qs(parsed.query or "")
                sid = str(qs.get("session_id", [""])[0] or "").strip()
                if not sid:
                    self._send_json(400, {"ok": False, "error": "missing_session_id"})
                    return
                bundle = self._project_access(name)
                if not bundle.get("can_read_project"):
                    self._send_json(403, {"ok": False, "error": "project_forbidden"})
                    return
                self.send_response(200)
                self.send_header("Content-Type", "text/event-stream; charset=utf-8")
                self.send_header("Cache-Control", "no-store")
                self.send_header("Connection", "keep-alive")
                self.send_header("X-Accel-Buffering", "no")
                self.end_headers()
                seq = 0
                try:
                    while True:
                        merged = merge_docs_health_session_view(
                            self.workspace_root, name, sid
                        )
                        if merged is None:
                            payload = {"ok": False, "error": "session_not_found", "seq": seq}
                            line = "data: " + json.dumps(payload, default=str) + "\n\n"
                            self.wfile.write(line.encode("utf-8"))
                            self.wfile.flush()
                            break
                        payload = {"ok": True, "session": merged, "seq": seq}
                        line = "data: " + json.dumps(payload, default=str) + "\n\n"
                        self.wfile.write(line.encode("utf-8"))
                        self.wfile.flush()
                        seq += 1
                        time.sleep(0.85)
                except (BrokenPipeError, ConnectionResetError, OSError):
                    return
                return
            if tail == "forge-runs":
                from lenses.platform_selfhost_runs import (
                    list_forge_runs,
                    load_forge_run_bundle,
                )

                bundle = self._project_access(name)
                if not bundle.get("can_read_project"):
                    self._send_json(403, {"ok": False, "error": "project_forbidden"})
                    return
                child_path = bundle.get("child_path")
                if not isinstance(child_path, Path):
                    self._send_json(404, {"ok": False, "error": "not_found"})
                    return
                fr_qs = urllib.parse.parse_qs(parsed.query or "").get("run_id", [])
                rid = str(fr_qs[0]).strip() if fr_qs else ""
                if rid:
                    payload = load_forge_run_bundle(child_path, rid)
                else:
                    payload = list_forge_runs(child_path)
                code = 200 if payload.get("ok") else 404
                self._send_json(code, payload)
                return
            if tail == "docs-health":
                from lenses.docs_health.api_handlers import get_project_docs_health

                bundle = self._project_access(name)
                get_project_docs_health(
                    self.workspace_root,
                    self.registry,
                    name,
                    bundle=bundle,
                    send_json=self._send_json,
                    query=parsed.query or "",
                )
                return
            err = json.dumps({"error": "not_found"}).encode("utf-8")
            self._send(404, err, "application/json; charset=utf-8")
            return

        if parsed.path.startswith("/docs"):
            doc_path = _safe_docs_path(parsed.path)
            if doc_path is None:
                self._send(404, _docs_missing_html(), "text/html; charset=utf-8")
                return
            mime, _ = mimetypes.guess_type(str(doc_path))
            ctype = mime or "application/octet-stream"
            if doc_path.suffix.lower() == ".html":
                ctype = "text/html; charset=utf-8"
            data = doc_path.read_bytes()
            if ctype.startswith("text/html"):
                data = inject_studio_iframe_nav_bridge(data)
            self._send(200, data, ctype)
            return

        state = self._scan(git_extended=True, force_refresh=force_refresh)

        path_only_nrm = parsed.path.split("?", 1)[0]
        if path_only_nrm == "/nested-roadmap-view.html":
            from lenses.nested_roadmap_workspace import nested_roadmap_view_document_bytes

            data = nested_roadmap_view_document_bytes(
                LENSES_REPO_ROOT,
                self.workspace_root,
                state,
                parsed.query or "",
            )
            data = inject_studio_iframe_nav_bridge(data)
            self._send(200, data, "text/html; charset=utf-8")
            return

        path_only_view = parsed.path.split("?", 1)[0]
        if path_only_view == "/view/docs" or path_only_view.startswith("/view/docs/"):
            iframe_src = _iframe_src_for_view_docs(path_only_view)
            exists = _safe_docs_path(iframe_src) is not None
            tail = path_only_view[len("/view/docs") :].lstrip("/")
            page_title = (
                f"Reference · {tail}"
                if tail
                else "Lenses reference"
            )
            bc_docs = (
                ("/", "Overview"),
                (view_lenses_docs_href(), "Reference"),
                ("", page_title),
            )
            miss = None
            if not exists:
                miss = (
                    "This reference page is not available (file missing or docs not built). "
                    "Run `python3 generator/build-lenses-docs.py` from the forge-lenses repo if needed."
                )
            html = page_view_embed(
                state,
                iframe_src=iframe_src,
                raw_open_href=iframe_src,
                page_title=page_title,
                breadcrumb_parts=bc_docs,
                lenses_repo_root=LENSES_REPO_ROOT,
                handbook_url=handbook_url,
                forge_url=forge_url,
                missing_message=miss,
            ).encode("utf-8")
            self._send(200, html, "text/html; charset=utf-8")
            return

        if path_only_view.startswith("/view/local-site/"):
            iframe_src = _iframe_src_for_view_local_site(path_only_view)
            if iframe_src is None:
                self._send(
                    404,
                    _local_site_missing_html(),
                    "text/html; charset=utf-8",
                )
                return
            lp_if = _local_site_site_and_tail(iframe_src)
            exists = False
            if lp_if is not None:
                sn, tl = lp_if
                exists = (
                    _safe_local_site_file(
                        self.workspace_root, self.registry, sn, tl
                    )
                    is not None
                )
            tail_show = path_only_view[len("/view/local-site/") :].strip("/")
            site_guess = tail_show.split("/")[0] if tail_show else ""
            page_title = (
                f"Preview · {tail_show}"
                if tail_show
                else f"Preview · {site_guess or 'site'}"
            )
            bc_ls = (
                ("/", "Overview"),
                ("/websites", "Sites"),
                ("", page_title),
            )
            miss = None
            if not exists:
                miss = (
                    "This preview path was not found under the workspace static site output "
                    "(build the site or check the path)."
                )
            html = page_view_embed(
                state,
                iframe_src=iframe_src,
                raw_open_href=iframe_src,
                page_title=page_title,
                breadcrumb_parts=bc_ls,
                lenses_repo_root=LENSES_REPO_ROOT,
                handbook_url=handbook_url,
                forge_url=forge_url,
                missing_message=miss,
            ).encode("utf-8")
            self._send(200, html, "text/html; charset=utf-8")
            return

        if path == "/feature-showcase":
            html = page_feature_showcase(
                state,
                self.registry,
                handbook_url,
                forge_url,
                LENSES_REPO_ROOT,
            ).encode("utf-8")
            self._send(200, html, "text/html; charset=utf-8")
            return

        if path == "/search":
            qs_s = urllib.parse.parse_qs(parsed.query or "")
            qv = qs_s.get("q", [])
            q = str(qv[0]).strip() if qv else ""
            lim_raw = qs_s.get("limit", [])
            off_raw = qs_s.get("offset", [])
            try:
                page_limit = int(str(lim_raw[0]).strip()) if lim_raw else 25
            except ValueError:
                page_limit = 25
            try:
                page_offset = int(str(off_raw[0]).strip()) if off_raw else 0
            except ValueError:
                page_offset = 0
            repo_raw = qs_s.get("repo", []) or qs_s.get("site", [])
            scope_repo = str(repo_raw[0]).strip() if repo_raw else ""
            ridx = qs_s.get("reindex", [])
            rnotice = str(ridx[0]).strip().lower() if ridx else ""
            reindex_notice: str | None = (
                rnotice
                if rnotice in ("started", "busy", "forbidden")
                else None
            )
            hits: list[dict[str, Any]] = []
            total = 0
            if q:
                conn = search_db.connect(self.workspace_root)
                try:
                    result = search_db.search(
                        conn,
                        q,
                        limit=page_limit,
                        offset=page_offset,
                        scope_site=scope_repo,
                    )
                    hits = result["hits"]
                    total = int(result["total"])
                    page_limit = int(result["limit"])
                    page_offset = int(result["offset"])
                finally:
                    conn.close()
            html = page_search(
                state,
                self.registry,
                handbook_url,
                forge_url,
                LENSES_REPO_ROOT,
                query=q,
                hits=hits,
                total=total,
                limit=page_limit,
                offset=page_offset,
                scope_repo=scope_repo or None,
                reindex_notice=reindex_notice,
            ).encode("utf-8")
            self._send(200, html, "text/html; charset=utf-8")
            return

        if path == "/overview/charts-api":
            html = page_overview_charts_api(
                state,
                self.registry,
                handbook_url,
                forge_url,
                LENSES_REPO_ROOT,
            )
            if html is None:
                html = "<!DOCTYPE html><html><body><p>Kitchensink not available</p></body></html>"
            self._send(200, html.encode("utf-8"), "text/html; charset=utf-8")
            return

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
            child_path = resolve_workspace_child_dir(
                self.workspace_root, project_name, self.registry
            )
            if child_path is None:
                self._send(404, b"Unknown project", "text/plain; charset=utf-8")
                return
            bundle = self._project_access(project_name)
            if not bundle.get("can_read_project"):
                self._send(
                    403,
                    (
                        "<!DOCTYPE html><html><head><meta charset=utf-8><title>Access denied</title></head>"
                        "<body><h1>Access denied</h1><p>Sign in with GitHub (PAT) or ask a workspace admin "
                        f"for access to project <code>{project_name}</code>.</p>"
                        '<p><a href="/">Workspace home</a></p></body></html>'
                    ).encode("utf-8"),
                    "text/html; charset=utf-8",
                )
                return
            if len(segments) >= 2:
                sub = segments[1].strip().lower()
                if sub == "charts-api":
                    html = page_project_charts_api(
                        state,
                        self.registry,
                        project_name,
                        child_path,
                        handbook_url,
                        forge_url,
                        LENSES_REPO_ROOT,
                    )
                    if html is None:
                        html = "<!DOCTYPE html><html><body><p>Kitchensink not available</p></body></html>"
                    self._send(200, html.encode("utf-8"), "text/html; charset=utf-8")
                    return
                if sub != "strategy":
                    self._send(404, b"Not found", "text/plain; charset=utf-8")
                    return
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
            html = inject_studio_iframe_nav_bridge(html)
            self._send(200, html, "text/html; charset=utf-8")
            return
        if path == "/wbs":
            html = page_wbs(
                state,
                handbook_url,
                forge_url,
                LENSES_REPO_ROOT,
                self.workspace_root,
                self.registry,
            ).encode("utf-8")
            self._send(200, html, "text/html; charset=utf-8")
            return
        if path == "/roadmaps":
            loc = "/plan"
            q = parsed.query
            if q:
                loc = f"{loc}?{q}"
            self.send_response(302)
            self.send_header("Location", loc)
            self.send_header("Content-Length", "0")
            self.end_headers()
            return
        if path == "/plan":
            qs_plan = urllib.parse.parse_qs(parsed.query or "")
            html = page_plan(
                state, handbook_url, forge_url, LENSES_REPO_ROOT, qs_plan
            ).encode("utf-8")
            self._send(200, html, "text/html; charset=utf-8")
            return
        if path == "/timeline":
            qs = urllib.parse.parse_qs(parsed.query or "")
            html = page_timeline(
                state, handbook_url, forge_url, LENSES_REPO_ROOT, qs
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
            html = page_wbs_view(
                rel,
                text,
                handbook_url,
                forge_url,
                LENSES_REPO_ROOT,
                state=state,
            ).encode("utf-8")
            self._send(200, html, "text/html; charset=utf-8")
            return
        if path == "/workspace-md/view":
            qs = urllib.parse.parse_qs(parsed.query or "")
            rels = qs.get("p", [])
            if not rels:
                self._send(400, b"Missing p=", "text/plain; charset=utf-8")
                return
            rel = rels[0]
            sp = safe_forge_workspace_file(self.workspace_root, rel)
            if sp is None:
                self._send(404, b"Not found or not allowed", "text/plain; charset=utf-8")
                return
            text = sp.read_text(encoding="utf-8", errors="replace")
            html = page_workspace_md_view(
                rel,
                text,
                handbook_url,
                forge_url,
                LENSES_REPO_ROOT,
                state=state,
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
            if found:
                proj_slug, ent = found
                bundle = self._project_access(proj_slug)
                is_sup = bool(bundle.get("is_workspace_super_admin"))
                cr = bool(bundle.get("can_read_project"))
                if not can_view_sticker_board(
                    self._session_login(),
                    ent,
                    is_workspace_super_admin=is_sup,
                    can_read_project=cr,
                ):
                    self._send(
                        403,
                        b"Access denied for this sticker board",
                        "text/plain; charset=utf-8",
                    )
                    return
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
                session_login=self._session_login(),
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
        if parsed.path.startswith("/stickerboard/api"):
            parsed = parsed._replace(path=normalize_stickerboard_api_path(parsed.path))
            self.path = parsed.path + (f"?{parsed.query}" if parsed.query else "")
        post_path = parsed.path.rstrip("/") or "/"

        if self._route_access_blocked(post_path, "POST"):
            return

        if post_path.startswith("/api/agent-runtime"):
            client_ip = self.client_address[0]
            if not client_may_run_shell_actions(client_ip):
                self._send_json(
                    403,
                    {
                        "ok": False,
                        "error": "agent_runtime_api_allowed_from_loopback_or_lenses_allow_actions",
                    },
                )
                return
            from lenses.agent_runtime.http import handle_agent_runtime_post

            body = self._read_json_body(max_len=256_000)
            if handle_agent_runtime_post(self.workspace_root, post_path, body, send_json=self._send_json):
                return

        if post_path.rstrip("/") == "/api/bridge/links":
            from lenses.bridge.api_handlers import handle_bridge_post

            body = self._read_json_body(max_len=64_000)
            if handle_bridge_post(
                workspace_root=self.workspace_root,
                post_path=post_path,
                body=body,
                send_json=self._send_json,
                client_ip=self.client_address[0],
                may_run_actions=client_may_run_shell_actions,
            ):
                return

        if (
            post_path.startswith("/api/artifacts")
            or post_path.startswith("/api/decisions")
            or post_path == "/api/review-packs"
            or post_path == "/api/assay-packets"
        ):
            from lenses.bridge.methodology_http import handle_methodology_b2_post

            body = self._read_json_body(max_len=512_000)
            if handle_methodology_b2_post(
                workspace_root=self.workspace_root,
                post_path=post_path,
                body=body,
                send_json=self._send_json,
                client_ip=self.client_address[0],
                may_run_actions=client_may_run_shell_actions,
            ):
                return

        if post_path.startswith("/api/agents"):
            from lenses.bridge.agentic_http import handle_agentic_b3_post

            body = self._read_json_body(max_len=512_000)
            if handle_agentic_b3_post(
                workspace_root=self.workspace_root,
                post_path=post_path,
                body=body,
                send_json=self._send_json,
                client_ip=self.client_address[0],
                may_run_actions=client_may_run_shell_actions,
            ):
                return

        if post_path.startswith("/api/ceremonies"):
            from lenses.bridge.ceremony_http import handle_ceremony_b4_post

            body = self._read_json_body(max_len=512_000)
            if handle_ceremony_b4_post(
                workspace_root=self.workspace_root,
                post_path=post_path,
                body=body,
                send_json=self._send_json,
                client_ip=self.client_address[0],
                may_run_actions=client_may_run_shell_actions,
            ):
                return

        if post_path.startswith("/api/handoffs") or post_path.startswith("/api/execution-sessions"):
            from lenses.bridge.handoff_http import handle_handoff_b5_post

            body = self._read_json_body(max_len=512_000)
            if handle_handoff_b5_post(
                workspace_root=self.workspace_root,
                post_path=post_path,
                body=body,
                send_json=self._send_json,
                client_ip=self.client_address[0],
                may_run_actions=client_may_run_shell_actions,
            ):
                return

        if post_path.startswith("/api/outcomes") or post_path.startswith("/api/launches"):
            from lenses.bridge.outcome_http import handle_outcome_b6_post

            body = self._read_json_body(max_len=512_000)
            if handle_outcome_b6_post(
                workspace_root=self.workspace_root,
                post_path=post_path,
                body=body,
                send_json=self._send_json,
                client_ip=self.client_address[0],
                may_run_actions=client_may_run_shell_actions,
            ):
                return

        if post_path == "/api/orchestration/seed-demo":
            from lenses.orchestration_graph.db import connect
            from lenses.orchestration_graph.feature_flag import experimental_orchestration_graph_enabled
            from lenses.orchestration_graph.seed_demo import force_reload_demo

            if not experimental_orchestration_graph_enabled():
                self._send_json(404, {"ok": False, "error": "feature_disabled"})
                return
            client_ip = self.client_address[0]
            if not client_may_run_shell_actions(client_ip):
                self._send_json(
                    403,
                    {"ok": False, "error": "allowed_from_loopback_or_lenses_allow_actions"},
                )
                return
            conn = connect(self.workspace_root)
            if conn is None:
                self._send_json(503, {"ok": False, "error": "graph_unavailable"})
                return
            try:
                out = force_reload_demo(conn)
                self._send_json(200, out)
            except OSError as ex:
                self._send_json(500, {"ok": False, "error": str(ex)})
            finally:
                conn.close()
            return

        if post_path == "/api/llm/settings":
            client_ip = self.client_address[0]
            if not client_may_run_shell_actions(client_ip):
                self._send_json(
                    403,
                    {"ok": False, "error": "llm_api_allowed_from_loopback_or_lenses_allow_actions"},
                )
                return
            body = self._read_json_body(max_len=256_000)
            st_in = body.get("settings") if isinstance(body.get("settings"), dict) else body
            if not isinstance(st_in, dict):
                self._send_json(400, {"ok": False, "error": "missing_settings"})
                return
            from lenses.llm_settings_store import merge_save, save_raw

            merged = merge_save(self.workspace_root, st_in)
            save_raw(self.workspace_root, merged)
            self._send_json(200, {"ok": True})
            return
        if post_path == "/api/fleet/settings":
            client_ip = self.client_address[0]
            if not client_may_run_shell_actions(client_ip):
                self._send_json(
                    403,
                    {"ok": False, "error": "llm_api_allowed_from_loopback_or_lenses_allow_actions"},
                )
                return
            body = self._read_json_body(max_len=512_000)
            st_in = body.get("settings") if isinstance(body.get("settings"), dict) else body
            if not isinstance(st_in, dict):
                self._send_json(400, {"ok": False, "error": "missing_settings"})
                return
            from lenses.fleet_settings_store import merge_save, save_raw

            merged = merge_save(self.workspace_root, st_in)
            save_raw(self.workspace_root, merged)
            self._send_json(200, {"ok": True})
            return
        if post_path == "/api/fleet/probe":
            client_ip = self.client_address[0]
            if not client_may_run_shell_actions(client_ip):
                self._send_json(
                    403,
                    {"ok": False, "error": "llm_api_allowed_from_loopback_or_lenses_allow_actions"},
                )
                return
            import lenses.sandbox.fleet_client as fleet_cli

            self._send_json(200, fleet_cli.probe_health(self.workspace_root))
            return
        if post_path == "/api/fleet/test-fleet":
            client_ip = self.client_address[0]
            if not client_may_run_shell_actions(client_ip):
                self._send_json(
                    403,
                    {"ok": False, "error": "llm_api_allowed_from_loopback_or_lenses_allow_actions"},
                )
                return
            body = self._read_json_body(max_len=16_000)
            count = 5
            if isinstance(body, dict) and body.get("count") is not None:
                try:
                    count = int(body["count"])
                except (TypeError, ValueError):
                    count = 5
            import lenses.sandbox.fleet_client as fleet_cli

            out = fleet_cli.run_test_fleet_batch(self.workspace_root, count=count)
            self._send_json(200, out)
            return
        if post_path == "/api/fleet/discover":
            client_ip = self.client_address[0]
            if not client_may_run_shell_actions(client_ip):
                self._send_json(
                    403,
                    {"ok": False, "error": "llm_api_allowed_from_loopback_or_lenses_allow_actions"},
                )
                return
            body = self._read_json_body(max_len=32_000)
            if not isinstance(body, dict):
                body = {}
            from lenses.fleet_lan_discover import run_discovery

            mode = str(body.get("mode") or "quick").strip().lower()
            if mode not in ("quick", "subnet"):
                mode = "quick"
            ports_raw = body.get("ports")
            ports: list[int] | None = None
            if isinstance(ports_raw, list):
                ports = []
                for p in ports_raw:
                    try:
                        ports.append(int(p))
                    except (TypeError, ValueError):
                        pass
            extra = body.get("hosts")
            hosts_extra: list[str] | None = None
            if isinstance(extra, list):
                hosts_extra = [str(x).strip() for x in extra if str(x).strip()]
            global_token = str(body.get("global_token") or "").strip()
            timeout_s = 0.45
            if body.get("timeout_s") is not None:
                try:
                    timeout_s = min(5.0, max(0.15, float(body["timeout_s"])))
                except (TypeError, ValueError):
                    timeout_s = 0.45
            out = run_discovery(
                mode=mode,
                ports=ports,
                extra_hosts=hosts_extra,
                global_token=global_token,
                timeout_s=timeout_s,
            )
            self._send_json(200, out)
            return
        if post_path == "/api/fleet/node-detail":
            client_ip = self.client_address[0]
            if not client_may_run_shell_actions(client_ip):
                self._send_json(
                    403,
                    {"ok": False, "error": "llm_api_allowed_from_loopback_or_lenses_allow_actions"},
                )
                return
            body = self._read_json_body(max_len=16_000)
            if not isinstance(body, dict):
                body = {}
            import lenses.sandbox.fleet_client as fleet_cli

            nid = str(body.get("node_id") or "").strip()
            include_snap = body.get("include_snapshot", True)
            if isinstance(include_snap, str):
                include_snap = include_snap.strip().lower() in ("1", "true", "yes", "on")
            else:
                include_snap = bool(include_snap)
            self._send_json(200, fleet_cli.describe_fleet_node(self.workspace_root, nid, include_snapshot=include_snap))
            return
        if post_path == "/api/fleet/connect-forge-llm":
            client_ip = self.client_address[0]
            if not client_may_run_shell_actions(client_ip):
                self._send_json(
                    403,
                    {"ok": False, "error": "llm_api_allowed_from_loopback_or_lenses_allow_actions"},
                )
                return
            body = self._read_json_body(max_len=32_000)
            if not isinstance(body, dict):
                self._send_json(400, {"ok": False, "error": "expected_json_object"})
                return
            from lenses.fleet_llm_connect import connect_forge_llm_to_llm_settings

            self._send_json(200, connect_forge_llm_to_llm_settings(self.workspace_root, body))
            return
        if post_path == "/api/llm/provider-probe":
            client_ip = self.client_address[0]
            if not client_may_run_shell_actions(client_ip):
                self._send_json(
                    403,
                    {"ok": False, "error": "llm_api_allowed_from_loopback_or_lenses_allow_actions"},
                )
                return
            body = self._read_json_body(max_len=32_000)
            provider = str(body.get("provider", "")).strip().lower()
            action = str(body.get("action", "models") or "models").strip().lower()
            if not provider:
                self._send_json(400, {"ok": False, "error": "missing_provider"})
                return
            from lenses.llm_provider_probe import discover_models, health_ping
            from lenses.llm_usage_store import record_provider_probe

            probe_kw: dict[str, Any] = {}
            if isinstance(body, dict):
                if "probe_openai_compatible_base_url" in body:
                    probe_kw["compat_base_probe"] = str(body.get("probe_openai_compatible_base_url", ""))
                if "probe_openai_compatible_bearer" in body:
                    probe_kw["compat_bearer_probe"] = str(body.get("probe_openai_compatible_bearer", ""))

            if action == "health":
                hp = health_ping(self.workspace_root, provider, **probe_kw)
                record_provider_probe(self.workspace_root, provider, action, hp)
                self._send_json(200, hp)
            else:
                dm = discover_models(self.workspace_root, provider, **probe_kw)
                record_provider_probe(self.workspace_root, provider, action, dm)
                self._send_json(200, dm)
            return
        if post_path == "/api/llm/routing-preview-draft":
            client_ip = self.client_address[0]
            if not client_may_run_shell_actions(client_ip):
                self._send_json(
                    403,
                    {"ok": False, "error": "llm_api_allowed_from_loopback_or_lenses_allow_actions"},
                )
                return
            body = self._read_json_body(max_len=256_000)
            overlay = body.get("settings") if isinstance(body.get("settings"), dict) else body
            if not isinstance(overlay, dict):
                self._send_json(400, {"ok": False, "error": "missing_settings"})
                return
            from lenses.llm_resolve import build_routing_preview

            self._send_json(200, build_routing_preview(self.workspace_root, overlay=overlay))
            return
        if post_path == "/api/llm/ollama-action":
            client_ip = self.client_address[0]
            if not client_may_run_shell_actions(client_ip):
                self._send_json(
                    403,
                    {"ok": False, "error": "llm_api_allowed_from_loopback_or_lenses_allow_actions"},
                )
                return
            body = self._read_json_body(max_len=8_000)
            act = str(body.get("action", "")).strip().lower()
            model = str(body.get("model", "")).strip()
            if not model:
                self._send_json(400, {"ok": False, "error": "missing_model"})
                return
            if not re.match(r"^[a-zA-Z0-9][a-zA-Z0-9._:\-+]*$", model):
                self._send_json(400, {"ok": False, "error": "invalid_model"})
                return
            from lenses import ollama_admin

            if act in ("pull", "update"):
                self._send_json(200, ollama_admin.ollama_pull(model))
            elif act in ("delete", "remove"):
                self._send_json(200, ollama_admin.ollama_delete(model))
            else:
                self._send_json(400, {"ok": False, "error": "unknown_action"})
            return
        if post_path == "/api/llm/chat":
            client_ip = self.client_address[0]
            if not client_may_run_shell_actions(client_ip):
                self._send_json(
                    403,
                    {
                        "ok": False,
                        "error": "llm_chat_allowed_from_loopback_or_lenses_allow_actions",
                    },
                )
                return
            body = self._read_json_body(max_len=256_000)
            provider = str(body.get("provider", "")).strip()
            message = str(body.get("message", ""))
            model_raw = body.get("model")
            model_override: str | None
            if model_raw is None:
                model_override = None
            else:
                ms = str(model_raw).strip()
                model_override = ms if ms else None
            refine = bool(body.get("refine"))
            stid_raw = body.get("studio_task_id")
            studio_task_id = str(stid_raw).strip() if stid_raw is not None else None
            studio_task_id = studio_task_id if studio_task_id else None
            result = llm_chat_api.chat(
                provider,
                message,
                model_override,
                workspace_root=self.workspace_root,
                refine=refine,
                studio_task_id=studio_task_id,
            )
            self._send_json(200, result)
            return

        if post_path == "/api/sdlc-copilot/chat-async":
            client_ip = self.client_address[0]
            if not client_may_run_shell_actions(client_ip):
                self._send_json(
                    403,
                    {
                        "ok": False,
                        "error": "llm_chat_allowed_from_loopback_or_lenses_allow_actions",
                    },
                )
                return
            import copy
            import threading

            from lenses.access_policy import load_policy
            from lenses.sdlc_copilot.chat import parse_sdlc_copilot_request_body, run_copilot_chat_multi
            from lenses.sdlc_copilot.copilot_async_session import append_event, create_session, set_session_status
            from lenses.sdlc_copilot.feature_flag import experimental_sdlc_copilot_enabled
            from lenses.sdlc_copilot.permissions import may_use_propose_writes

            if not experimental_sdlc_copilot_enabled():
                self._send_json(404, {"ok": False, "error": "feature_disabled"})
                return
            body = self._read_json_body(max_len=256_000)
            p = parse_sdlc_copilot_request_body(body)
            tool_mode = str(p["tool_mode"])
            project_slug = p["project_slug"]
            policy = load_policy(self.workspace_root)
            login = self._session_login()
            if tool_mode == "propose_writes" and not may_use_propose_writes(
                policy, login, project_slug
            ):
                self._send_json(
                    403,
                    {
                        "ok": False,
                        "error": "copilot_propose_writes_forbidden",
                        "detail": "Requires GitHub session with write access to project_slug when RBAC is enforced.",
                    },
                )
                return
            scan_state = self._scan(git_extended=False, force_refresh=False)
            scan_snap = copy.deepcopy(scan_state)
            sid = create_session(self.workspace_root)
            set_session_status(self.workspace_root, sid, "running")
            wr = self.workspace_root
            msg = str(p["message"])

            def job() -> None:
                try:

                    def emit(typ: str, payload: dict) -> None:
                        append_event(wr, sid, typ, payload)

                    emit("thought", {"message": "Starting multi-step Copilot…"})
                    out = run_copilot_chat_multi(
                        workspace_root=wr,
                        provider=str(p["provider"]),
                        user_message=msg,
                        model_override=p["model_override"],
                        refine=bool(p["refine"]),
                        tool_mode=tool_mode,
                        route=str(p["route"]),
                        project_slug=project_slug,
                        entity_id=p["entity_id"],
                        scope_site=str(p["scope_site"]),
                        login=login,
                        scan_state=scan_snap,
                        studio_task_id=p["studio_task_id"],
                        page_context_summary=p["page_context_summary"],
                        related_md_rel_paths=p["related_md_rel_paths"],
                        studio_chat_mode=p["studio_chat_mode"],
                        max_rounds=p.get("copilot_max_rounds"),
                        on_event=emit,
                    )
                    append_event(wr, sid, "final", {"result": out})
                    set_session_status(wr, sid, "done")
                except Exception as ex:  # noqa: BLE001
                    append_event(
                        wr,
                        sid,
                        "error",
                        {"message": str(ex)[:800], "type": type(ex).__name__},
                    )
                    set_session_status(wr, sid, "error")

            threading.Thread(target=job, daemon=True).start()
            self._send_json(200, {"ok": True, "session_id": sid})
            return

        if post_path == "/api/sdlc-copilot/chat":
            client_ip = self.client_address[0]
            if not client_may_run_shell_actions(client_ip):
                self._send_json(
                    403,
                    {
                        "ok": False,
                        "error": "llm_chat_allowed_from_loopback_or_lenses_allow_actions",
                    },
                )
                return
            from lenses.access_policy import load_policy
            from lenses.sdlc_copilot.chat import parse_sdlc_copilot_request_body, run_copilot_chat
            from lenses.sdlc_copilot.feature_flag import experimental_sdlc_copilot_enabled
            from lenses.sdlc_copilot.permissions import may_use_propose_writes

            if not experimental_sdlc_copilot_enabled():
                self._send_json(404, {"ok": False, "error": "feature_disabled"})
                return
            body = self._read_json_body(max_len=256_000)
            p = parse_sdlc_copilot_request_body(body)
            tool_mode = str(p["tool_mode"])
            project_slug = p["project_slug"]
            policy = load_policy(self.workspace_root)
            login = self._session_login()
            if tool_mode == "propose_writes" and not may_use_propose_writes(
                policy, login, project_slug
            ):
                self._send_json(
                    403,
                    {
                        "ok": False,
                        "error": "copilot_propose_writes_forbidden",
                        "detail": "Requires GitHub session with write access to project_slug when RBAC is enforced.",
                    },
                )
                return

            scan_state = self._scan(git_extended=False, force_refresh=False)
            out = run_copilot_chat(
                workspace_root=self.workspace_root,
                provider=str(p["provider"]),
                user_message=str(p["message"]),
                model_override=p["model_override"],
                refine=bool(p["refine"]),
                tool_mode=tool_mode,
                route=str(p["route"]),
                project_slug=project_slug,
                entity_id=p["entity_id"],
                scope_site=str(p["scope_site"]),
                login=login,
                scan_state=scan_state,
                studio_task_id=p["studio_task_id"],
                page_context_summary=p["page_context_summary"],
                related_md_rel_paths=p["related_md_rel_paths"],
                studio_chat_mode=p["studio_chat_mode"],
            )
            self._send_json(200, out)
            return

        if post_path == "/api/sdlc-copilot/topic-archive":
            client_ip = self.client_address[0]
            if not client_may_run_shell_actions(client_ip):
                self._send_json(
                    403,
                    {
                        "ok": False,
                        "error": "llm_chat_allowed_from_loopback_or_lenses_allow_actions",
                    },
                )
                return
            from lenses.sdlc_copilot.feature_flag import experimental_sdlc_copilot_enabled
            from lenses.sdlc_copilot.topic_archive import archive_copilot_topic

            if not experimental_sdlc_copilot_enabled():
                self._send_json(404, {"ok": False, "error": "feature_disabled"})
                return
            body = self._read_json_body(max_len=512_000)
            out = archive_copilot_topic(self.workspace_root, body)
            self._send_json(200 if out.get("ok") else 400, out)
            return

        if post_path == "/api/sdlc-copilot/commit-proposal":
            client_ip = self.client_address[0]
            if not client_may_run_shell_actions(client_ip):
                self._send_json(
                    403,
                    {
                        "ok": False,
                        "error": "llm_chat_allowed_from_loopback_or_lenses_allow_actions",
                    },
                )
                return
            from lenses.sdlc_copilot.commit import commit_stored_proposal

            body = self._read_json_body(max_len=64_000)
            proposal_id = str(body.get("proposal_id") or "").strip()
            confirm = bool(body.get("confirm"))
            login = self._session_login()
            result = commit_stored_proposal(
                self.workspace_root,
                proposal_id,
                login=login,
                confirm=confirm,
            )
            code = 200 if result.get("ok") else 400
            if result.get("error") == "proposal_not_found":
                code = 404
            elif result.get("error") in ("copilot_commit_forbidden", "confirm_required"):
                code = 403 if result.get("error") == "copilot_commit_forbidden" else 400
            self._send_json(code, result)
            return

        if post_path == "/api/blueprints/wizard/session":
            from lenses.blueprints_wizard.api import post_create_session
            from lenses.blueprints_wizard.feature_flag import experimental_blueprints_wizard_enabled

            if not experimental_blueprints_wizard_enabled():
                self._send_json(404, {"ok": False, "error": "feature_disabled"})
                return
            self._read_json_body(max_len=256_000)
            out = post_create_session(self.workspace_root)
            self._send_json(200, out)
            return

        if post_path == "/api/blueprints/wizard/telemetry":
            from lenses.blueprints_wizard.api import post_wizard_telemetry_event
            from lenses.blueprints_wizard.feature_flag import experimental_blueprints_wizard_enabled

            if not experimental_blueprints_wizard_enabled():
                self._send_json(404, {"ok": False, "error": "feature_disabled"})
                return
            body = self._read_json_body(max_len=16_000)
            out = post_wizard_telemetry_event(self.workspace_root, body)
            self._send_json(200 if out.get("ok") else 400, out)
            return

        _refine_sid = None
        if post_path.startswith("/api/blueprints/wizard/session/") and post_path.endswith("/refine"):
            from lenses.blueprints_wizard.api import parse_session_refine_path

            _refine_sid = parse_session_refine_path(post_path)
        if _refine_sid is not None:
            from lenses.blueprints_wizard.api import post_refine_session
            from lenses.blueprints_wizard.feature_flag import experimental_blueprints_wizard_enabled

            if not experimental_blueprints_wizard_enabled():
                self._send_json(404, {"ok": False, "error": "feature_disabled"})
                return
            client_ip = self.client_address[0]
            if not client_may_run_shell_actions(client_ip):
                self._send_json(
                    403,
                    {
                        "ok": False,
                        "error": "llm_chat_allowed_from_loopback_or_lenses_allow_actions",
                    },
                )
                return
            body = self._read_json_body(max_len=256_000)
            out = post_refine_session(self.workspace_root, _refine_sid, body)
            if out.get("ok"):
                self._send_json(200, out)
                return
            err = str(out.get("error", ""))
            if err == "not_found":
                self._send_json(404, out)
            elif err in ("invalid_session_id", "missing_notes", "empty_model_output"):
                self._send_json(400, out)
            elif err == "save_failed" or "invalid_session" in err:
                self._send_json(500, out)
            else:
                self._send_json(200, out)
            return

        _interpret_sid = None
        if post_path.startswith("/api/blueprints/wizard/session/") and post_path.endswith("/interpret"):
            from lenses.blueprints_wizard.api import parse_session_interpret_path

            _interpret_sid = parse_session_interpret_path(post_path)
        if _interpret_sid is not None:
            from lenses.blueprints_wizard.api import post_interpret_session
            from lenses.blueprints_wizard.feature_flag import experimental_blueprints_wizard_enabled

            if not experimental_blueprints_wizard_enabled():
                self._send_json(404, {"ok": False, "error": "feature_disabled"})
                return
            client_ip = self.client_address[0]
            if not client_may_run_shell_actions(client_ip):
                self._send_json(
                    403,
                    {
                        "ok": False,
                        "error": "llm_chat_allowed_from_loopback_or_lenses_allow_actions",
                    },
                )
                return
            body = self._read_json_body(max_len=256_000)
            out = post_interpret_session(self.workspace_root, _interpret_sid, body)
            if out.get("ok"):
                self._send_json(200, out)
                return
            err = str(out.get("error", ""))
            if err == "not_found":
                self._send_json(404, out)
            elif err in (
                "invalid_session_id",
                "missing_notes",
                "empty_model_output",
                "interpretation_parse_error",
                "invalid_provider",
                "interpretation_invalid",
            ):
                self._send_json(400, out)
            elif err == "save_failed" or "invalid_session" in err:
                self._send_json(500, out)
            else:
                self._send_json(200, out)
            return

        _clarify_suggest_sid = None
        if post_path.startswith("/api/blueprints/wizard/session/") and post_path.endswith(
            "/clarify-suggest"
        ):
            from lenses.blueprints_wizard.api import parse_session_clarify_suggest_path

            _clarify_suggest_sid = parse_session_clarify_suggest_path(post_path)
        if _clarify_suggest_sid is not None:
            from lenses.blueprints_wizard.api import post_clarify_suggest_session
            from lenses.blueprints_wizard.feature_flag import experimental_blueprints_wizard_enabled

            if not experimental_blueprints_wizard_enabled():
                self._send_json(404, {"ok": False, "error": "feature_disabled"})
                return
            client_ip = self.client_address[0]
            if not client_may_run_shell_actions(client_ip):
                self._send_json(
                    403,
                    {
                        "ok": False,
                        "error": "llm_chat_allowed_from_loopback_or_lenses_allow_actions",
                    },
                )
                return
            body = self._read_json_body(max_len=256_000)
            out = post_clarify_suggest_session(self.workspace_root, _clarify_suggest_sid, body)
            if out.get("ok"):
                self._send_json(200, out)
                return
            err = str(out.get("error", ""))
            if err == "not_found":
                self._send_json(404, out)
            elif err in (
                "invalid_session_id",
                "invalid_provider",
                "missing_message",
                "clarification_parse_error",
            ):
                self._send_json(400, out)
            else:
                self._send_json(200, out)
            return

        _gen_art_sid = None
        if post_path.startswith("/api/blueprints/wizard/session/") and post_path.endswith(
            "/generate-artifacts"
        ):
            from lenses.blueprints_wizard.api import parse_session_generate_artifacts_path

            _gen_art_sid = parse_session_generate_artifacts_path(post_path)
        if _gen_art_sid is not None:
            from lenses.blueprints_wizard.api import post_generate_artifacts
            from lenses.blueprints_wizard.feature_flag import experimental_blueprints_wizard_enabled

            if not experimental_blueprints_wizard_enabled():
                self._send_json(404, {"ok": False, "error": "feature_disabled"})
                return
            client_ip = self.client_address[0]
            if not client_may_run_shell_actions(client_ip):
                self._send_json(
                    403,
                    {
                        "ok": False,
                        "error": "llm_chat_allowed_from_loopback_or_lenses_allow_actions",
                    },
                )
                return
            body = self._read_json_body(max_len=256_000)
            _t_gen = time.monotonic()
            out = post_generate_artifacts(self.workspace_root, _gen_art_sid, body)
            from lenses.blueprints_wizard.wizard_telemetry import record_http_api_result

            record_http_api_result(
                self.workspace_root,
                api="generate_artifacts",
                session_id=_gen_art_sid,
                out=out,
                started_at_mono=_t_gen,
            )
            if out.get("ok"):
                self._send_json(200, out)
                return
            err = str(out.get("error", ""))
            if err == "not_found":
                self._send_json(404, out)
            elif err in (
                "invalid_session_id",
                "invalid_provider",
                "invalid_artifact_key",
                "invalid_artifact_keys",
                "upstream_not_approved",
                "prerequisites_not_met",
                "run_plan_needs_title",
                "run_plan_needs_steps",
                "run_plan_too_many_steps",
                "run_plan_step_needs_title",
                "invalid_run_plan",
                "invalid_run_plan_step",
                "empty_model_output",
                "artifact_generation_parse_error",
                "artifact_locked",
                "scope_incomplete",
            ):
                self._send_json(400, out)
            elif err == "save_failed" or "invalid_session" in err:
                self._send_json(500, out)
            else:
                self._send_json(200, out)
            return

        _art_rev_sid = None
        if post_path.startswith("/api/blueprints/wizard/session/") and post_path.endswith(
            "/artifact-review"
        ):
            from lenses.blueprints_wizard.api import parse_session_artifact_review_path

            _art_rev_sid = parse_session_artifact_review_path(post_path)
        if _art_rev_sid is not None:
            from lenses.blueprints_wizard.api import post_artifact_review
            from lenses.blueprints_wizard.feature_flag import experimental_blueprints_wizard_enabled

            if not experimental_blueprints_wizard_enabled():
                self._send_json(404, {"ok": False, "error": "feature_disabled"})
                return
            client_ip = self.client_address[0]
            if not client_may_run_shell_actions(client_ip):
                self._send_json(
                    403,
                    {
                        "ok": False,
                        "error": "llm_chat_allowed_from_loopback_or_lenses_allow_actions",
                    },
                )
                return
            body = self._read_json_body(max_len=256_000)
            out = post_artifact_review(self.workspace_root, _art_rev_sid, body)
            if out.get("ok"):
                self._send_json(200, out)
                return
            err = str(out.get("error", ""))
            if err == "not_found":
                self._send_json(404, out)
            elif err in (
                "invalid_session_id",
                "invalid_artifact_key",
                "invalid_review_action",
                "artifact_not_found",
                "artifact_locked",
                "artifact_not_locked",
                "approve_bundle_blocked",
            ):
                self._send_json(400, out)
            elif err == "save_failed" or "invalid_session" in err:
                self._send_json(500, out)
            else:
                self._send_json(400, out)
            return

        _art_export_sid = None
        if post_path.startswith("/api/blueprints/wizard/session/") and post_path.endswith(
            "/artifact-export"
        ):
            from lenses.blueprints_wizard.api import parse_session_artifact_export_path

            _art_export_sid = parse_session_artifact_export_path(post_path)
        if _art_export_sid is not None:
            from lenses.blueprints_wizard.api import post_artifact_export
            from lenses.blueprints_wizard.feature_flag import experimental_blueprints_wizard_enabled

            if not experimental_blueprints_wizard_enabled():
                self._send_json(404, {"ok": False, "error": "feature_disabled"})
                return
            client_ip = self.client_address[0]
            if not client_may_run_shell_actions(client_ip):
                self._send_json(
                    403,
                    {
                        "ok": False,
                        "error": "llm_chat_allowed_from_loopback_or_lenses_allow_actions",
                    },
                )
                return
            body = self._read_json_body(max_len=256_000)
            out = post_artifact_export(self.workspace_root, _art_export_sid, body)
            if out.get("ok"):
                self._send_json(200, out)
                return
            err = str(out.get("error", ""))
            if err == "not_found":
                self._send_json(404, out)
            elif err in (
                "invalid_session_id",
                "invalid_artifact_key",
                "invalid_artifact_keys",
            ):
                self._send_json(400, out)
            elif err == "save_failed" or "invalid_session" in err:
                self._send_json(500, out)
            else:
                self._send_json(400, out)
            return

        _clp_preview_sid = None
        if post_path.startswith("/api/blueprints/wizard/session/") and post_path.endswith(
            "/cursor-launch-pack/preview"
        ):
            from lenses.blueprints_wizard.api import parse_session_cursor_launch_pack_path

            _clp_preview_sid = parse_session_cursor_launch_pack_path(post_path, "preview")
        if _clp_preview_sid is not None:
            from lenses.blueprints_wizard.api import post_cursor_launch_pack_preview
            from lenses.blueprints_wizard.feature_flag import experimental_blueprints_wizard_enabled

            if not experimental_blueprints_wizard_enabled():
                self._send_json(404, {"ok": False, "error": "feature_disabled"})
                return
            body = self._read_json_body(max_len=256_000)
            out = post_cursor_launch_pack_preview(self.workspace_root, _clp_preview_sid, body)
            if out.get("ok"):
                self._send_json(200, out)
                return
            err = str(out.get("error", ""))
            if err == "not_found":
                self._send_json(404, out)
            elif err in ("invalid_session_id", "invalid_artifact_keys", "strict_approval_failed"):
                self._send_json(400, out)
            else:
                self._send_json(400, out)
            return

        _clp_export_sid = None
        if post_path.startswith("/api/blueprints/wizard/session/") and post_path.endswith(
            "/cursor-launch-pack/export"
        ):
            from lenses.blueprints_wizard.api import parse_session_cursor_launch_pack_path

            _clp_export_sid = parse_session_cursor_launch_pack_path(post_path, "export")
        if _clp_export_sid is not None:
            from lenses.blueprints_wizard.api import post_cursor_launch_pack_export
            from lenses.blueprints_wizard.feature_flag import experimental_blueprints_wizard_enabled

            if not experimental_blueprints_wizard_enabled():
                self._send_json(404, {"ok": False, "error": "feature_disabled"})
                return
            client_ip = self.client_address[0]
            if not client_may_run_shell_actions(client_ip):
                self._send_json(
                    403,
                    {
                        "ok": False,
                        "error": "llm_chat_allowed_from_loopback_or_lenses_allow_actions",
                    },
                )
                return
            body = self._read_json_body(max_len=512_000)
            out = post_cursor_launch_pack_export(self.workspace_root, _clp_export_sid, body)
            if out.get("ok"):
                self._send_json(200, out)
                return
            err = str(out.get("error", ""))
            if err == "not_found":
                self._send_json(404, out)
            elif err in (
                "invalid_session_id",
                "invalid_artifact_keys",
                "invalid_destination",
                "invalid_relative_path",
                "strict_approval_failed",
            ):
                self._send_json(400, out)
            elif err == "save_failed" or "invalid_session" in err:
                self._send_json(500, out)
            else:
                self._send_json(400, out)
            return

        _art_recheck_sid = None
        if post_path.startswith("/api/blueprints/wizard/session/") and post_path.endswith(
            "/artifact-recheck"
        ):
            from lenses.blueprints_wizard.api import parse_session_artifact_recheck_path

            _art_recheck_sid = parse_session_artifact_recheck_path(post_path)
        if _art_recheck_sid is not None:
            from lenses.blueprints_wizard.api import post_artifact_recheck
            from lenses.blueprints_wizard.feature_flag import experimental_blueprints_wizard_enabled

            if not experimental_blueprints_wizard_enabled():
                self._send_json(404, {"ok": False, "error": "feature_disabled"})
                return
            client_ip = self.client_address[0]
            if not client_may_run_shell_actions(client_ip):
                self._send_json(
                    403,
                    {
                        "ok": False,
                        "error": "llm_chat_allowed_from_loopback_or_lenses_allow_actions",
                    },
                )
                return
            body = self._read_json_body(max_len=256_000)
            _t_recheck = time.monotonic()
            out = post_artifact_recheck(self.workspace_root, _art_recheck_sid, body)
            from lenses.blueprints_wizard.wizard_telemetry import record_http_api_result

            record_http_api_result(
                self.workspace_root,
                api="artifact_recheck",
                session_id=_art_recheck_sid,
                out=out,
                started_at_mono=_t_recheck,
            )
            if out.get("ok"):
                self._send_json(200, out)
                return
            err = str(out.get("error", ""))
            if err == "not_found":
                self._send_json(404, out)
            elif err == "invalid_session_id":
                self._send_json(400, out)
            elif err == "save_failed" or "invalid_session" in err:
                self._send_json(500, out)
            else:
                self._send_json(400, out)
            return

        _create_repo_sid = None
        if post_path.startswith("/api/blueprints/wizard/session/") and post_path.endswith(
            "/create-repo"
        ):
            from lenses.blueprints_wizard.api import parse_session_create_repo_path

            _create_repo_sid = parse_session_create_repo_path(post_path)
        if _create_repo_sid is not None:
            from lenses.blueprints_wizard.api import post_create_repo
            from lenses.blueprints_wizard.feature_flag import experimental_blueprints_wizard_enabled

            if not experimental_blueprints_wizard_enabled():
                self._send_json(404, {"ok": False, "error": "feature_disabled"})
                return
            client_ip = self.client_address[0]
            if not client_may_run_shell_actions(client_ip):
                self._send_json(
                    403,
                    {
                        "ok": False,
                        "error": "create_repo_allowed_from_loopback_or_lenses_allow_actions",
                    },
                )
                return
            body = self._read_json_body(max_len=256_000)
            out = post_create_repo(self.workspace_root, _create_repo_sid, body)
            if out.get("ok"):
                self._send_json(200, out)
                return
            err = str(out.get("error", ""))
            if err == "not_found":
                self._send_json(404, out)
            elif err in ("invalid_session_id", "confirmation_required"):
                self._send_json(400, out)
            elif err in ("missing_github_token", "missing_repo_name", "missing_owner"):
                self._send_json(400, out)
            elif err == "github_http_error":
                self._send_json(502, out)
            else:
                self._send_json(400, out)
            return

        if post_path == "/api/auth/github":
            self._post_api_auth_github()
            return
        if post_path == "/api/auth/logout":
            self._post_api_auth_logout()
            return
        if post_path == "/api/auth/loopback-dev-login":
            self._post_api_auth_loopback_dev_login()
            return
        if post_path == "/api/access/set-member":
            self._post_api_access_set_member()
            return
        if post_path == "/api/actions/run":
            self._post_api_actions_run()
            return
        if post_path == "/api/sticker-board-share/join":
            self._post_api_sticker_board_share_join()
            return

        if post_path == "/api/sticker-board-share":
            self._post_api_sticker_board_share()
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
        if post_path == "/api/wbs/create":
            self._post_api_wbs_create()
            return
        if post_path == "/api/search/reindex":
            self._post_api_search_reindex()
            return
        if post_path == "/api/search/ingest":
            self._post_api_search_ingest()
            return
        if post_path == "/api/forgesdlc-blog/sync":
            client_ip = self.client_address[0]
            if not client_may_run_shell_actions(client_ip):
                self._send_json(
                    403,
                    {
                        "ok": False,
                        "error": "sync_allowed_from_loopback_or_lenses_allow_actions",
                    },
                )
                return
            sync_qs = urllib.parse.parse_qs(parsed.query or "")
            force_vals = sync_qs.get("force", [])
            force = bool(force_vals) and str(force_vals[0]).strip().lower() in (
                "1",
                "true",
                "yes",
            )
            from lenses.forgesdlc_blog import sync_blog_cache
            from lenses.governance.audit_log import KIND_CONNECTOR_SYNC, append_event

            payload = sync_blog_cache(self.workspace_root, force=force)
            if payload.get("ok"):
                append_event(
                    self.workspace_root,
                    kind=KIND_CONNECTOR_SYNC,
                    actor=self._session_login(),
                    resource="forgesdlc-blog:/sync",
                    detail={"force": force, "keys": list(payload.keys())[:12]},
                )
            self._send_json(200, payload)
            return

        api_proj = _parse_api_project_subpath(post_path)
        if api_proj is not None and api_proj[1] == "forge-run-decision":
            from lenses.platform_selfhost_runs import patch_for_decision

            name, _tail_d = api_proj
            client_ip = self.client_address[0]
            if not client_may_run_shell_actions(client_ip):
                self._send_json(
                    403,
                    {
                        "ok": False,
                        "error": "decision_writes_require_loopback_or_lenses_allow_actions",
                    },
                )
                return
            bundle = self._project_access(name)
            if not bundle.get("can_write_project"):
                self._send_json(403, {"ok": False, "error": "project_forbidden"})
                return
            child_path = bundle.get("child_path")
            if not isinstance(child_path, Path):
                self._send_json(404, {"ok": False, "error": "not_found"})
                return
            body = self._read_json_body(max_len=32_000)
            rid = str(body.get("forge_run_id") or "").strip()
            state = str(body.get("state") or "").strip()
            ho = body.get("human_owner")
            human_owner = str(ho).strip() if ho not in (None, "") else None
            out = patch_for_decision(
                child_path, rid, state=state, human_owner=human_owner
            )
            self._send_json(200 if out.get("ok") else 400, out)
            return

        if api_proj is not None and api_proj[1] == "docs-health":
            from lenses.docs_health.api_handlers import post_project_docs_health

            body = self._read_json_body(max_len=512_000)
            post_project_docs_health(
                self.workspace_root,
                self.registry,
                api_proj[0],
                body,
                bundle=self._project_access(api_proj[0]),
                send_json=self._send_json,
            )
            return

        api_proj = _parse_api_project_subpath(post_path)
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

        policy = load_policy(self.workspace_root)
        if is_policy_enforced(policy):
            sess = self._session_login()
            if not sess:
                self._send_json(
                    403,
                    {
                        "ok": False,
                        "error": "auth_required",
                        "stdout": "",
                        "stderr": "",
                        "exit_code": -1,
                    },
                )
                return
            bundle = project_access_bundle(
                self.workspace_root, self.registry, name, sess
            )
            if not bundle.get("can_write_project"):
                self._send_json(
                    403,
                    {
                        "ok": False,
                        "error": "project_forbidden",
                        "stdout": "",
                        "stderr": "",
                        "exit_code": -1,
                    },
                )
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

    def do_PUT(self) -> None:  # noqa: N802
        parsed = urllib.parse.urlparse(self.path)
        put_path = parsed.path.rstrip("/") or "/"
        from lenses.blueprints_wizard.api import parse_session_path, put_session
        from lenses.blueprints_wizard.feature_flag import experimental_blueprints_wizard_enabled

        if not put_path.startswith("/api/blueprints/wizard/session/"):
            self._send(404, b"Not found", "text/plain; charset=utf-8")
            return
        if not experimental_blueprints_wizard_enabled():
            self._send_json(404, {"ok": False, "error": "feature_disabled"})
            return
        sid = parse_session_path(put_path)
        if sid is None:
            self._send_json(400, {"ok": False, "error": "invalid_session_id"})
            return
        body = self._read_json_body(max_len=256_000)
        out = put_session(self.workspace_root, sid, body)
        if not out.get("ok"):
            err = str(out.get("error", ""))
            if err == "not_found":
                self._send_json(404, out)
            elif err == "invalid_session_id":
                self._send_json(400, out)
            elif err == "invalid_session":
                self._send_json(400, out)
            else:
                self._send_json(400, out)
            return
        self._send_json(200, out)

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
        policy = bootstrap_on_first_auth(self.workspace_root, login)
        if not can_sign_in(policy, login):
            self._send_json(
                403,
                {
                    "ok": False,
                    "error": "access_denied_not_invited",
                    "github_login": login,
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

    def _post_api_access_set_member(self) -> None:
        client_ip = self.client_address[0]
        if not client_may_run_shell_actions(client_ip):
            self._send_json(
                403,
                {"ok": False, "error": "access_api_loopback_only"},
            )
            return
        sess = self._session_login()
        if not sess:
            self._send_json(403, {"ok": False, "error": "auth_required"})
            return
        body = self._read_json_body()
        project = str(body.get("project", "")).strip()
        target = str(body.get("login", "")).strip()
        role = str(body.get("role", ROLE_MEMBER)).strip()
        remove = str(body.get("action", "set")).strip().lower() == "remove"
        disciplines_raw = body.get("disciplines")
        disc_list: list[str] | None = None
        if isinstance(disciplines_raw, list):
            disc_list = [str(x).strip() for x in disciplines_raw if str(x).strip()]

        if not project or (not remove and not target):
            self._send_json(
                400,
                {"ok": False, "error": "missing_project_or_login"},
            )
            return
        if not remove and role not in (
            ROLE_VIEWER,
            ROLE_MEMBER,
            ROLE_DISCIPLINE_POWER,
        ):
            self._send_json(400, {"ok": False, "error": "invalid_role"})
            return

        scopes_raw = body.get("scopes")
        scope_list: list[str] | None = None
        if isinstance(scopes_raw, list):
            scope_list = [str(x).strip() for x in scopes_raw if str(x).strip()]

        policy = load_policy(self.workspace_root)
        if is_super_admin(policy, sess):
            if remove:
                new_pol = remove_project_member(policy, project, target)
            else:
                new_pol = set_project_member(
                    policy,
                    project,
                    target,
                    role=role,
                    disciplines=disc_list,
                    scopes=scope_list,
                )
            save_policy(self.workspace_root, new_pol)
            from lenses.governance.audit_log import KIND_DATA_CHANGE, append_event

            append_event(
                self.workspace_root,
                kind=KIND_DATA_CHANGE,
                actor=sess,
                resource=f"access:project:{project}:member",
                project_slug=project,
                detail={
                    "action": "remove" if remove else "set",
                    "target_login": target,
                    "role": None if remove else role,
                    "scopes": scope_list,
                },
            )
            self._send_json(200, {"ok": True})
            return

        if not can_manage_access(policy, sess, project):
            self._send_json(403, {"ok": False, "error": "forbidden"})
            return
        if role not in (ROLE_VIEWER, ROLE_MEMBER):
            self._send_json(403, {"ok": False, "error": "forbidden_role"})
            return
        if disc_list and not power_user_may_assign_disciplines(
            policy, sess, project, disc_list
        ):
            self._send_json(403, {"ok": False, "error": "discipline_scope"})
            return
        if remove:
            new_pol = remove_project_member(policy, project, target)
        else:
            new_pol = set_project_member(
                policy,
                project,
                target,
                role=role,
                disciplines=disc_list,
                scopes=scope_list,
            )
        save_policy(self.workspace_root, new_pol)
        from lenses.governance.audit_log import KIND_DATA_CHANGE, append_event

        append_event(
            self.workspace_root,
            kind=KIND_DATA_CHANGE,
            actor=sess,
            resource=f"access:project:{project}:member",
            project_slug=project,
            detail={
                "action": "remove" if remove else "set",
                "target_login": target,
                "role": None if remove else role,
                "scopes": scope_list,
            },
        )
        self._send_json(200, {"ok": True})

    def _post_api_actions_run(self) -> None:
        client_ip = self.client_address[0]
        if not client_may_run_shell_actions(client_ip):
            self._send_json(
                403,
                {"ok": False, "error": "actions_allowed_from_loopback_only"},
            )
            return
        sm = self.session_manager
        ck = _cookie_value(self.headers.get("Cookie"), SESSION_COOKIE)
        sess_login = sm.session_login(ck) if sm else None
        if not sess_login:
            self._send_json(
                403,
                {
                    "ok": False,
                    "error": "auth_required",
                    "hint": "POST /api/auth/github with a PAT.",
                },
            )
            return
        body = self._read_json_body()
        site = str(body.get("site", "")).strip()
        action = str(body.get("action", "")).strip()
        if not site or not action:
            self._send_json(400, {"ok": False, "error": "missing_site_or_action"})
            return
        bundle = project_access_bundle(
            self.workspace_root, self.registry, site, sess_login
        )
        if not bundle.get("can_write_project"):
            self._send_json(
                403,
                {"ok": False, "error": "project_forbidden"},
            )
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

    def _get_api_sticker_board_share(self, parsed: urllib.parse.ParseResult) -> None:
        qs = urllib.parse.parse_qs(parsed.query or "")
        token = str(qs.get("token", [""])[0]).strip()
        if not is_valid_share_token(token):
            self._send_json(400, {"ok": False, "error": "invalid_share_token"})
            return
        meta, err = share_metadata(self.workspace_root, token)
        if not meta:
            self._send_json(404, {"ok": False, "error": err or "share_not_found"})
            return
        self._send_json(200, meta)

    def _post_api_sticker_board_share(self) -> None:
        scope = self._share_scope()
        if scope:
            self._send_json(403, {"ok": False, "error": "share_scope_forbidden"})
            return
        client_ip = self.client_address[0]
        login = resolve_facilitator_login(
            self._session_login(),
            client_ip=client_ip,
            workspace_root=self.workspace_root,
        )
        if not login:
            self._send_json(401, {"ok": False, "error": "login_required"})
            return
        body = self._read_json_body(max_len=16_000)
        act = str(body.get("action", "")).strip().lower()
        if act == "start":
            board_id = str(body.get("board_id", "")).strip()
            if not is_valid_board_id(board_id):
                self._send_json(400, {"ok": False, "error": "invalid_board_id"})
                return
            reg = load_registry_raw(self.workspace_root)
            found = find_board_entry(reg, board_id)
            if not found:
                self._send_json(404, {"ok": False, "error": "board_not_found"})
                return
            proj_slug, ent = found
            bundle = self._project_access(proj_slug)
            if not can_edit_sticker_board(
                login,
                ent,
                is_workspace_super_admin=bool(bundle.get("is_workspace_super_admin")),
                can_write_project=bool(bundle.get("can_write_project")),
            ):
                self._send_json(403, {"ok": False, "error": "sticker_board_forbidden"})
                return
            guest_role = str(body.get("guest_role", "view")).strip().lower()
            result, err = share_start(
                self.workspace_root,
                board_id=board_id,
                guest_role=guest_role,
                created_by_login=login,
                request_origin=self._absolute_origin(),
            )
            if not result:
                self._send_json(400, {"ok": False, "error": err})
                return
            self._send_json(200, result)
            return
        if act == "revoke":
            token = str(body.get("share_token", "")).strip()
            ok, err = share_revoke(
                self.workspace_root,
                share_token=token,
                actor_login=login,
            )
            if not ok:
                code = 404 if err == "share_not_found" else 403
                self._send_json(code, {"ok": False, "error": err})
                return
            self._send_json(200, {"ok": True})
            return
        self._send_json(400, {"ok": False, "error": "unknown_action"})

    def _client_is_loopback(self) -> bool:
        ip = self.client_address[0]
        if ip in ("127.0.0.1", "::1", "localhost"):
            return True
        try:
            return ipaddress.ip_address(ip).is_loopback
        except ValueError:
            return False

    def _post_api_auth_loopback_dev_login(self) -> None:
        if not stickerboard_loopback_dev_auth_enabled():
            self._send_json(403, {"ok": False, "error": "loopback_dev_auth_disabled"})
            return
        if not self._client_is_loopback():
            self._send_json(403, {"ok": False, "error": "loopback_only"})
            return
        sm = self.session_manager
        if sm is None:
            self._send_json(500, {"ok": False, "error": "session_store_unavailable"})
            return
        login = LOCAL_LOOPBACK_FACILITATOR_LOGIN
        policy = bootstrap_on_first_auth(self.workspace_root, login)
        if not can_sign_in(policy, login):
            self._send_json(403, {"ok": False, "error": "access_denied_not_invited"})
            return
        sid = sm.create_session(
            login,
            auth_provider="loopback_dev",
            display_name="Local developer",
        )
        cookie = (
            f"{SESSION_COOKIE}={sid}; HttpOnly; SameSite=Lax; Path=/; "
            f"Max-Age={SESSION_MAX_AGE_SEC}"
        )
        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Set-Cookie", cookie)
        payload = json.dumps(
            {"ok": True, "session_login": login, "auth_provider": "loopback_dev"}
        ).encode("utf-8")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def _post_api_sticker_board_share_join(self) -> None:
        login = self._session_login()
        session_cookie: str | None = None
        if not login and stickerboard_loopback_dev_auth_enabled() and self._client_is_loopback():
            sm = self.session_manager
            if sm is None:
                self._send_json(500, {"ok": False, "error": "session_store_unavailable"})
                return
            login = LOCAL_LOOPBACK_FACILITATOR_LOGIN
            policy = bootstrap_on_first_auth(self.workspace_root, login)
            if not can_sign_in(policy, login):
                self._send_json(403, {"ok": False, "error": "access_denied_not_invited"})
                return
            sid = sm.create_session(
                login,
                auth_provider="loopback_dev",
                display_name="Local developer",
            )
            session_cookie = (
                f"{SESSION_COOKIE}={sid}; HttpOnly; SameSite=Lax; Path=/; "
                f"Max-Age={SESSION_MAX_AGE_SEC}"
            )
        if not login:
            self._send_json(401, {"ok": False, "error": "login_required"})
            return
        body = self._read_json_body(max_len=8_000)
        token = str(body.get("share_token", "")).strip()
        if not is_valid_share_token(token):
            self._send_json(400, {"ok": False, "error": "invalid_share_token"})
            return
        prof = self._session_profile() or {}
        display_name = prof.get("display_name") or login
        email = prof.get("email")
        result, err = share_join(
            self.workspace_root,
            share_token=token,
            login=login,
            display_name=display_name,
            email=email,
        )
        if not result:
            code = 404 if err in ("share_not_found", "share_revoked") else 400
            self._send_json(code, {"ok": False, "error": err})
            return
        board_id = str(result.get("board_id") or "")
        guest_role = str(result.get("guest_role") or "view")
        share_add_guest_acl(
            self.workspace_root,
            board_id,
            login,
            guest_role,
        )
        scope_cookie = (
            f"{SHARE_SCOPE_COOKIE}={token}; HttpOnly; SameSite=Lax; Path=/; "
            f"Max-Age={SESSION_MAX_AGE_SEC}"
        )
        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        if session_cookie:
            self.send_header("Set-Cookie", session_cookie)
        self.send_header("Set-Cookie", scope_cookie)
        payload = json.dumps(
            {
                **result,
                "public_url": build_public_url(token, workspace_root=self.workspace_root),
            }
        ).encode(
            "utf-8"
        )
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def _post_api_sticker_board(self, parsed: urllib.parse.ParseResult) -> None:
        scope = self._share_scope()
        if scope and scope.get("guest_role") == "view":
            self._send_json(403, {"ok": False, "error": "view_guest_read_only"})
            return
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
        if scope:
            board_id = scope.get("board_id") or board_id
        if not is_valid_board_id(board_id):
            self._send_json(
                400,
                {"ok": False, "error": "missing_or_invalid_board_id"},
            )
            return
        if scope and board_id != scope.get("board_id"):
            self._send_json(401, {"ok": False, "error": "share_scope_board_mismatch"})
            return
        reg = load_registry_raw(self.workspace_root)
        found = find_board_entry(reg, board_id)
        if not found:
            self._send_json(400, {"ok": False, "error": "board_not_found"})
            return
        proj_slug, ent = found
        bundle = self._project_access(proj_slug)
        is_sup = bool(bundle.get("is_workspace_super_admin"))
        cw = bool(bundle.get("can_write_project"))
        sess = self._session_login()
        if scope:
            if scope.get("guest_role") != "edit":
                self._send_json(403, {"ok": False, "error": "sticker_board_forbidden"})
                return
        elif not can_edit_sticker_board(
            sess,
            ent,
            is_workspace_super_admin=is_sup,
            can_write_project=cw,
        ):
            self._send_json(
                403,
                {"ok": False, "error": "sticker_board_forbidden"},
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
        if scope and sess:
            prof = self._session_profile() or {}
            body = stamp_guest_score_attribution(
                body,
                session_login=sess,
                display_name=prof.get("display_name"),
            )
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
        sess = self._session_login()
        reg = load_registry_raw(self.workspace_root)

        if action == "create":
            project = str(payload.get("project", UNASSIGNED_PROJECT_KEY)).strip() or UNASSIGNED_PROJECT_KEY
            bundle = self._project_access(project)
            if not bundle.get("can_write_project"):
                self._send_json(
                    403,
                    {"ok": False, "error": "project_forbidden"},
                )
                return
            scan_payload = dict(payload)
            scan_payload["_workspace_scan_state"] = state
            ok, err, extra = registry_apply(
                self.workspace_root,
                self.expected_github_login,
                slugs,
                action,
                scan_payload,
                creator_login=sess,
            )
        elif action == "acl":
            board_id = str(payload.get("board_id", "")).strip()
            if not is_valid_board_id(board_id):
                self._send_json(400, {"ok": False, "error": "invalid_board_id"})
                return
            found = find_board_entry(reg, board_id)
            if not found:
                self._send_json(400, {"ok": False, "error": "board_not_found"})
                return
            proj_slug, ent = found
            bundle = self._project_access(proj_slug)
            policy = load_policy(self.workspace_root)
            can_m = can_manage_access(policy, sess, proj_slug)
            if not can_manage_board_acl(
                sess,
                ent,
                is_workspace_super_admin=bool(
                    bundle.get("is_workspace_super_admin")
                ),
                can_manage_project_access=can_m,
            ):
                self._send_json(
                    403,
                    {"ok": False, "error": "sticker_board_acl_forbidden"},
                )
                return
            ok, err, extra = registry_apply(
                self.workspace_root,
                self.expected_github_login,
                slugs,
                action,
                payload,
            )
        elif action == "repair_registry":
            ok, err, extra = registry_apply(
                self.workspace_root,
                self.expected_github_login,
                slugs,
                action,
                payload,
            )
        elif action in ("rename", "delete", "assign"):
            board_id = str(payload.get("board_id", "")).strip()
            if not is_valid_board_id(board_id):
                self._send_json(400, {"ok": False, "error": "invalid_board_id"})
                return
            found = find_board_entry(reg, board_id)
            if not found:
                self._send_json(400, {"ok": False, "error": "board_not_found"})
                return
            proj_slug, ent = found
            bundle = self._project_access(proj_slug)
            if not can_edit_sticker_board(
                sess,
                ent,
                is_workspace_super_admin=bool(
                    bundle.get("is_workspace_super_admin")
                ),
                can_write_project=bool(bundle.get("can_write_project")),
            ):
                self._send_json(
                    403,
                    {"ok": False, "error": "sticker_board_forbidden"},
                )
                return
            ok, err, extra = registry_apply(
                self.workspace_root,
                self.expected_github_login,
                slugs,
                action,
                payload,
            )
        else:
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

    def _post_api_wbs_create(self) -> None:
        client_ip = self.client_address[0]
        if not client_may_write_sticker_board(client_ip):
            self._send_json(
                403,
                {
                    "ok": False,
                    "error": (
                        "WBS create allowed from loopback only, "
                        "or set LENSES_ALLOW_GIT_ACTIONS=1"
                    ),
                },
            )
            return
        body = self._read_json_body()
        project = str(body.get("project", "")).strip()
        baseline = str(body.get("baseline_tag", "")).strip() or None
        new_tag = str(body.get("new_tag", "")).strip() or None
        if not project:
            self._send_json(400, {"ok": False, "error": "missing_project"})
            return
        result = create_wbs_md(
            self.workspace_root,
            self.registry,
            LENSES_REPO_ROOT,
            project,
            baseline_tag=baseline,
            new_tag=new_tag,
        )
        if result.get("ok"):
            self._bump_scan_cache()
        code = 200 if result.get("ok") else 400
        self._send_json(code, result)

    def _start_search_reindex_thread(self) -> str:
        """Return ``started`` | ``already_running`` | ``forbidden``."""
        client_ip = self.client_address[0]
        if not client_may_run_shell_actions(client_ip):
            return "forbidden"
        with _search_reindex_lock:
            if _search_reindex_status.get("running"):
                return "already_running"
            _search_reindex_status["running"] = True
            _search_reindex_status["last_error"] = None

        def run() -> None:
            try:
                r = reindex_workspace(
                    self.workspace_root,
                    LENSES_REPO_ROOT,
                    self.registry,
                )
                with _search_reindex_lock:
                    _search_reindex_status["running"] = False
                    _search_reindex_status["indexed"] = int(r.get("indexed", 0))
                    _search_reindex_status["skipped"] = int(r.get("skipped", 0))
                    _search_reindex_status["db_path"] = str(r.get("db_path", ""))
                    _search_reindex_status["last_error"] = None
                    _search_reindex_status["finished_at"] = time.time()
            except Exception as e:
                with _search_reindex_lock:
                    _search_reindex_status["running"] = False
                    _search_reindex_status["last_error"] = str(e)
                    _search_reindex_status["finished_at"] = time.time()

        threading.Thread(target=run, daemon=True).start()
        return "started"

    def _get_api_search_reindex(self, parsed: urllib.parse.ParseResult) -> None:
        """GET: optional ``redirect=/path`` → 303 to that path with ``reindex=`` query; else JSON like POST."""
        qs = urllib.parse.parse_qs(parsed.query or "")
        redirs = qs.get("redirect", [])
        st = self._start_search_reindex_thread()
        if st == "forbidden":
            self._send_json(
                403,
                {
                    "ok": False,
                    "error": "reindex_allowed_from_loopback_or_lenses_allow_actions",
                },
            )
            return
        if redirs:
            raw = str(redirs[0]).strip()
            safe = _safe_internal_redirect_path(raw)
            if safe is None:
                self._send_json(
                    400,
                    {"ok": False, "error": "invalid_redirect"},
                )
                return
            tag = "busy" if st == "already_running" else "started"
            if tag == "started":
                from lenses.governance.audit_log import KIND_CONNECTOR_SYNC, append_event

                append_event(
                    self.workspace_root,
                    kind=KIND_CONNECTOR_SYNC,
                    actor=self._session_login(),
                    resource="search:/reindex",
                    detail={"via": "GET_redirect", "status": "started"},
                )
            loc = _merge_query_param(safe, "reindex", tag)
            self.send_response(303)
            self.send_header("Location", loc)
            self.send_header("Content-Length", "0")
            self.end_headers()
            return
        if st == "already_running":
            self._send_json(
                409,
                {"ok": False, "error": "reindex_already_running"},
            )
            return
        if st == "started":
            from lenses.governance.audit_log import KIND_CONNECTOR_SYNC, append_event

            append_event(
                self.workspace_root,
                kind=KIND_CONNECTOR_SYNC,
                actor=self._session_login(),
                resource="search:/reindex",
                detail={"via": "GET", "status": "started"},
            )
        self._send_json(202, {"ok": True, "status": "started"})

    def _post_api_search_reindex(self) -> None:
        st = self._start_search_reindex_thread()
        if st == "forbidden":
            self._send_json(
                403,
                {
                    "ok": False,
                    "error": "reindex_allowed_from_loopback_or_lenses_allow_actions",
                },
            )
            return
        if st == "already_running":
            self._send_json(
                409,
                {"ok": False, "error": "reindex_already_running"},
            )
            return
        if st == "started":
            from lenses.governance.audit_log import KIND_CONNECTOR_SYNC, append_event

            append_event(
                self.workspace_root,
                kind=KIND_CONNECTOR_SYNC,
                actor=self._session_login(),
                resource="search:/reindex",
                detail={"via": "POST", "status": "started"},
            )
        self._send_json(202, {"ok": True, "status": "started"})

    def _post_api_search_ingest(self) -> None:
        client_ip = self.client_address[0]
        if not client_may_run_shell_actions(client_ip):
            self._send_json(
                403,
                {
                    "ok": False,
                    "error": "ingest_allowed_from_loopback_or_lenses_allow_actions",
                },
            )
            return
        body = self._read_json_body(max_len=600_000)
        url = str(body.get("url", "")).strip()
        title = str(body.get("title", "")).strip()
        text = str(body.get("text", "")).strip()
        if not url or not text:
            self._send_json(400, {"ok": False, "error": "missing_url_or_text"})
            return
        if len(text) > 512_000:
            self._send_json(400, {"ok": False, "error": "text_too_large"})
            return
        conn = search_db.connect(self.workspace_root)
        try:
            search_db.upsert_ingested(conn, url=url, title=title, body=text)
            conn.commit()
        finally:
            conn.close()
        self._send_json(200, {"ok": True})


def _maybe_start_search_reindex_on_startup(
    workspace_root: Path, registry: dict[str, Any]
) -> None:
    """Background FTS index of workspace HTML/Markdown when LENSES_SEARCH_REINDEX_ON_START is set.

    Used by the Electron shell so search is populated without a manual /api/search/reindex click.
    """
    v = os.environ.get("LENSES_SEARCH_REINDEX_ON_START", "").strip().lower()
    if v not in ("1", "true", "yes"):
        return

    def run() -> None:
        try:
            r = reindex_workspace(workspace_root, LENSES_REPO_ROOT, registry)
            idx = int(r.get("indexed", 0))
            sk = int(r.get("skipped", 0))
            print(
                f"[lenses] search reindex (startup): indexed={idx} skipped={sk}",
                file=sys.stderr,
            )
        except Exception as e:
            print(f"[lenses] search reindex (startup) failed: {e}", file=sys.stderr)

    threading.Thread(
        target=run,
        daemon=True,
        name="lenses-search-reindex-startup",
    ).start()


def _maybe_start_cursor_launch_staging_cleanup_thread(workspace_root: Path) -> None:
    """Periodic TTL cleanup for Blueprints Wizard staged download zips (experimental).

    Set ``LENSES_CURSOR_LAUNCH_STAGING_CLEANUP_INTERVAL_MIN`` to ``0`` / ``off`` to disable
    background sweeps (per-request cleanup still runs).

    Default when unset: **15** minutes between sweeps. First sweep runs immediately, then after
    each interval.
    """
    raw = os.environ.get("LENSES_CURSOR_LAUNCH_STAGING_CLEANUP_INTERVAL_MIN", "").strip().lower()
    if raw in ("0", "false", "no", "off"):
        return
    if not raw:
        interval_min = 15
    else:
        try:
            interval_min = int(raw)
        except ValueError:
            interval_min = 15
    if interval_min <= 0:
        return
    interval_sec = interval_min * 60

    def run() -> None:
        from lenses.blueprints_wizard.launch_pack_staging import cleanup_expired_staged_zips

        while True:
            try:
                n = cleanup_expired_staged_zips(workspace_root)
                if n:
                    print(
                        f"[lenses] cursor-launch-staging cleanup: removed {n} expired zip(s)",
                        file=sys.stderr,
                    )
            except Exception as e:
                print(f"[lenses] cursor-launch-staging cleanup failed: {e}", file=sys.stderr)
            time.sleep(interval_sec)

    threading.Thread(
        target=run,
        daemon=True,
        name="lenses-cursor-launch-staging-cleanup",
    ).start()


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

    # Vite (:5173 / :4173) calls /api on this process; CORS allowlist is loopback dev origins only.
    if args.host in ("127.0.0.1", "::1"):
        os.environ.setdefault("LENSES_ALLOW_DEV_CORS", "1")

    env_root = os.environ.get("LENSES_WORKSPACE_ROOT")
    ws = resolve_workspace_root(LENSES_REPO_ROOT, args.workspace_root, env_root)
    from lenses.auth_oidc import bootstrap_oidc_env_from_workspace
    from lenses.sticker_board_share import (
        bootstrap_stickerboard_env_from_workspace,
        bootstrap_stickerboard_public_from_workspace,
    )

    bootstrap_oidc_env_from_workspace(ws)
    bootstrap_stickerboard_env_from_workspace(ws)
    bootstrap_stickerboard_public_from_workspace(ws)
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
    _maybe_start_search_reindex_on_startup(ws, registry)
    _maybe_start_cursor_launch_staging_cleanup_thread(ws)

    sb_port_raw = (os.environ.get("LENSES_STICKERBOARD_PORT") or "9999").strip()
    try:
        sb_port = int(sb_port_raw)
    except ValueError:
        sb_port = 0
    sb_server: ThreadingHTTPServer | None = None
    if sb_port > 0 and args.host in ("127.0.0.1", "localhost", "::1"):
        class _StickerboardHandler(LensesHandler):
            stickerboard_port_only = True

        sb_server = ThreadingHTTPServer((args.host, sb_port), _StickerboardHandler)
        threading.Thread(
            target=sb_server.serve_forever,
            daemon=True,
            name="lenses-stickerboard-port",
        ).start()

    print(f"[lenses] http://{args.host}:{args.port}/")
    if sb_server is not None:
        print(f"[lenses] stickerboard http://{args.host}:{sb_port}/")
    print(f"[lenses] workspace_root={ws}")
    if exp_login:
        print(
            f"[lenses] expected_github_login={exp_login} (shared sticker path; sign-in uses lenses-access.json)"
        )
    else:
        print(
            "[lenses] expected_github_login not set — shared boards and auth need registry or .lenses-repo/"
        )
    print(f"[lenses] docs static from {DOCS_DIR} (run generator/build-lenses-docs.py if empty)")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n[lenses] stopped")


if __name__ == "__main__":
    main()
