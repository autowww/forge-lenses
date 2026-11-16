"""Discover and cache Forge SDLC blog posts from forgesdlc.com (sitemap + local HTML).

Cached under ``{workspace_root}/.lenses-local/forgesdlc-blog/``. Relative ``assets/`` in
cached HTML are resolved via optional ``<base href="https://forgesdlc.com/blog/">``
when serving so styling matches the live site when online; fully offline, CSS may not load.
"""

from __future__ import annotations

import json
import re
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

FORGESDLC_BLOG_PREFIX = "https://forgesdlc.com/blog/"
SITEMAP_URL = "https://forgesdlc.com/sitemap.xml"
MANIFEST_NAME = "manifest.json"
HTML_SUBDIR = "html"
USER_AGENT = "forge-lenses-forgesdlc-blog/1"

# Slug = last path segment; only these filenames are cached and served.
_SAFE_SLUG_RE = re.compile(r"^[a-z0-9][-a-z0-9]*\.html$", re.I)

_TITLE_RE = re.compile(rb"<title[^>]*>([^<]{0,800})", re.I)
# og:image — property before content, or content before property (forgesdlc.com order).
_OG_IMAGE_PROP_FIRST = re.compile(
    r'<meta\s+[^>]*property\s*=\s*["\']og:image["\'][^>]*\s+content\s*=\s*["\']([^"\']+)["\']',
    re.I,
)
_OG_IMAGE_CONTENT_FIRST = re.compile(
    r'<meta\s+[^>]*content\s*=\s*["\']([^"\']+)["\'][^>]*\s+property\s*=\s*["\']og:image["\']',
    re.I,
)

DEFAULT_OG_IMAGE_SUFFIX = "og-default.svg"


def blog_root_dir(workspace_root: Path) -> Path:
    return workspace_root.resolve() / ".lenses-local" / "forgesdlc-blog"


def html_cache_dir(workspace_root: Path) -> Path:
    return blog_root_dir(workspace_root) / HTML_SUBDIR


def manifest_path(workspace_root: Path) -> Path:
    return blog_root_dir(workspace_root) / MANIFEST_NAME


def is_allowed_forgesdlc_blog_url(url: str) -> bool:
    u = (url or "").strip()
    if not u.startswith(FORGESDLC_BLOG_PREFIX):
        return False
    try:
        parsed = urlparse(u)
    except ValueError:
        return False
    if parsed.netloc.lower() != "forgesdlc.com":
        return False
    if parsed.scheme not in ("http", "https"):
        return False
    seg = Path(parsed.path).name
    return bool(_SAFE_SLUG_RE.match(seg))


def slug_from_blog_url(url: str) -> str | None:
    if not is_allowed_forgesdlc_blog_url(url):
        return None
    return Path(urlparse(url).path).name.lower()


def parse_forgesdlc_blog_urls_from_sitemap(xml: str) -> list[dict[str, str]]:
    """Return ``[{url, lastmod}, ...]`` for forgesdlc.com ``/blog/*.html`` entries."""
    out: list[dict[str, str]] = []
    try:
        root = ET.fromstring(xml)
    except ET.ParseError:
        return out
    ns = {}
    if root.tag.startswith("{"):
        ns["sm"] = root.tag[1 : root.tag.index("}")]
        url_tag = "{%s}url" % ns["sm"]
        loc_tag = "{%s}loc" % ns["sm"]
        lastmod_tag = "{%s}lastmod" % ns["sm"]
    else:
        url_tag = "url"
        loc_tag = "loc"
        lastmod_tag = "lastmod"

    for url_el in root.iter(url_tag):
        loc_el = url_el.find(loc_tag)
        if loc_el is None or loc_el.text is None:
            continue
        raw_loc = loc_el.text.strip()
        if not raw_loc:
            continue
        if not is_allowed_forgesdlc_blog_url(raw_loc):
            continue
        lm_el = url_el.find(lastmod_tag)
        lastmod = (lm_el.text or "").strip() if lm_el is not None else ""
        out.append({"url": raw_loc, "lastmod": lastmod})
    return out


def _fetch_bytes(url: str, timeout: int = 45) -> tuple[bytes | None, str | None]:
    if not is_allowed_forgesdlc_blog_url(url) and url != SITEMAP_URL:
        return None, "url_not_allowed"
    req = urllib.request.Request(
        url,
        headers={"User-Agent": USER_AGENT, "Accept": "*/*"},
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.read(), None
    except urllib.error.HTTPError as e:
        try:
            body = e.read()[:200].decode("utf-8", errors="replace")
        except OSError:
            body = ""
        return None, f"http_{e.code}: {body}"
    except (urllib.error.URLError, OSError, TimeoutError) as e:
        return None, str(e)


def extract_title_from_html(html: bytes) -> str | None:
    m = _TITLE_RE.search(html)
    if not m:
        return None
    raw = m.group(1).decode("utf-8", errors="replace")
    t = re.sub(r"\s+", " ", raw).strip()
    if not t:
        return None
    for sep in (" · ", " - ", " | "):
        if sep in t:
            t = t.split(sep)[0].strip()
            break
    return t[:300] if t else None


def extract_og_image_from_html(html: bytes) -> str | None:
    """Return ``og:image`` URL from HTML ``<meta>`` tags, or ``None``."""
    try:
        text = html.decode("utf-8", errors="replace")
    except Exception:
        return None
    m = _OG_IMAGE_PROP_FIRST.search(text)
    if not m:
        m = _OG_IMAGE_CONTENT_FIRST.search(text)
    if not m:
        return None
    raw = m.group(1).strip()
    return raw if raw else None


def normalize_preview_image_url(url: str | None) -> str | None:
    """Drop site default OG image so Studio can show a neutral placeholder instead."""
    if not url or not str(url).strip():
        return None
    u = str(url).strip()
    try:
        parsed = urlparse(u)
        path = parsed.path or u
    except ValueError:
        path = u
    path_l = path.replace("\\", "/").lower()
    if path_l.endswith(DEFAULT_OG_IMAGE_SUFFIX.lower()):
        return None
    return u


def inject_base_href_after_head(html_bytes: bytes) -> bytes:
    """Insert ``<base href=\"https://forgesdlc.com/blog/\">`` after ``<head>`` if missing."""
    try:
        text = html_bytes.decode("utf-8", errors="replace")
    except Exception:
        return html_bytes
    if 'href="https://forgesdlc.com/blog/"' in text and "<base " in text.lower():
        return html_bytes
    lower = text.lower()
    idx = lower.find("<head")
    if idx < 0:
        return html_bytes
    gt = text.find(">", idx)
    if gt < 0:
        return html_bytes
    insert_at = gt + 1
    snippet = '<base href="https://forgesdlc.com/blog/" />'
    if snippet in text:
        return html_bytes
    return (text[:insert_at] + "\n  " + snippet + "\n" + text[insert_at:]).encode(
        "utf-8", errors="replace"
    )


def _load_manifest(workspace_root: Path) -> dict[str, Any]:
    p = manifest_path(workspace_root)
    if not p.is_file():
        return {"version": 1, "posts": []}
    try:
        raw = p.read_text(encoding="utf-8")
        data = json.loads(raw)
    except (OSError, json.JSONDecodeError):
        return {"version": 1, "posts": []}
    if not isinstance(data, dict):
        return {"version": 1, "posts": []}
    posts = data.get("posts")
    if not isinstance(posts, list):
        data["posts"] = []
    return data


def _save_manifest(workspace_root: Path, data: dict[str, Any]) -> None:
    root = blog_root_dir(workspace_root)
    root.mkdir(parents=True, exist_ok=True)
    manifest_path(workspace_root).write_text(
        json.dumps(data, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace(
        "+00:00", "Z"
    )


def _merge_post(
    existing: dict[str, Any] | None,
    url: str,
    lastmod: str,
    slug: str,
    title: str | None,
    cached_at: str,
    is_hub: bool,
    *,
    preview_image_url: str | None,
) -> dict[str, Any]:
    row: dict[str, Any] = {
        "url": url,
        "slug": slug,
        "lastmod": lastmod,
        "cached_at": cached_at,
        "is_hub": is_hub,
        "preview_image_url": preview_image_url,
    }
    if title:
        row["title"] = title
    elif existing and isinstance(existing.get("title"), str):
        row["title"] = existing["title"]
    return row


def sync_blog_cache(workspace_root: Path, force: bool = False) -> dict[str, Any]:
    """Fetch sitemap, refresh HTML for new/changed posts, update manifest.

    Returns payload suitable for ``GET /api/forgesdlc-blog`` (same shape as
    :func:`build_blog_payload` without sync).
    """
    wr = workspace_root.resolve()
    html_dir = html_cache_dir(wr)
    html_dir.mkdir(parents=True, exist_ok=True)

    manifest = _load_manifest(wr)
    last_err: str | None = None

    sm_bytes, sm_err = _fetch_bytes(SITEMAP_URL)
    if sm_bytes is None:
        last_err = sm_err or "sitemap_fetch_failed"
        manifest["last_sync_error"] = last_err
        manifest["synced_at"] = _utc_now_iso()
        _save_manifest(wr, manifest)
        return build_blog_payload(workspace_root)

    try:
        sm_text = sm_bytes.decode("utf-8", errors="replace")
    except Exception:
        sm_text = ""

    entries = parse_forgesdlc_blog_urls_from_sitemap(sm_text)
    if not entries:
        manifest["last_sync_error"] = last_err or "no_blog_urls_in_sitemap"
        manifest["synced_at"] = _utc_now_iso()
        _save_manifest(wr, manifest)
        return build_blog_payload(workspace_root)

    by_url = {e["url"]: e["lastmod"] for e in entries}

    prev_posts = manifest.get("posts")
    prev_by_slug: dict[str, dict[str, Any]] = {}
    if isinstance(prev_posts, list):
        for p in prev_posts:
            if isinstance(p, dict) and isinstance(p.get("slug"), str):
                prev_by_slug[p["slug"].lower()] = p

    updated_rows: list[dict[str, Any]] = []

    for url, lastmod in sorted(by_url.items(), key=lambda x: x[0]):
        slug = slug_from_blog_url(url)
        if not slug:
            continue
        is_hub = slug == "index.html"
        prev = prev_by_slug.get(slug)
        prev_lm = (prev or {}).get("lastmod") if isinstance(prev, dict) else None
        path = html_dir / slug
        need_fetch = (
            force
            or not path.is_file()
            or (isinstance(prev_lm, str) and prev_lm != lastmod)
            or (not isinstance(prev_lm, str) and lastmod)
        )

        title: str | None = None
        cached_at = _utc_now_iso()

        if need_fetch:
            body, err = _fetch_bytes(url)
            if body is None:
                last_err = last_err or err or f"fetch_failed:{slug}"
                preview_image_url: str | None = None
                if path.is_file():
                    cached_at = str(
                        (prev or {}).get("cached_at")
                        if isinstance(prev, dict)
                        and isinstance((prev or {}).get("cached_at"), str)
                        else _utc_now_iso()
                    )
                    raw = path.read_bytes()
                    title = extract_title_from_html(raw)
                    preview_image_url = normalize_preview_image_url(
                        extract_og_image_from_html(raw)
                    )
                else:
                    cached_at = _utc_now_iso()
                    title = (
                        (prev or {}).get("title")
                        if isinstance(prev, dict)
                        else None
                    )
                    if isinstance(prev, dict) and isinstance(
                        prev.get("preview_image_url"), str
                    ):
                        preview_image_url = prev["preview_image_url"]
                updated_rows.append(
                    _merge_post(
                        prev,
                        url,
                        lastmod,
                        slug,
                        title,
                        cached_at,
                        is_hub,
                        preview_image_url=preview_image_url,
                    )
                )
                continue
            path.write_bytes(body)
            title = extract_title_from_html(body)
            preview_image_url = normalize_preview_image_url(
                extract_og_image_from_html(body)
            )
            updated_rows.append(
                _merge_post(
                    prev,
                    url,
                    lastmod,
                    slug,
                    title,
                    cached_at,
                    is_hub,
                    preview_image_url=preview_image_url,
                )
            )
        else:
            cached_at = str(
                (prev or {}).get("cached_at")
                if isinstance(prev, dict) and isinstance((prev or {}).get("cached_at"), str)
                else _utc_now_iso()
            )
            title = None
            preview_image_url: str | None = None
            if path.is_file():
                raw = path.read_bytes()
                title = extract_title_from_html(raw)
                preview_image_url = normalize_preview_image_url(
                    extract_og_image_from_html(raw)
                )
            elif isinstance(prev, dict) and isinstance(prev.get("title"), str):
                title = prev.get("title")
            if preview_image_url is None and isinstance(prev, dict) and isinstance(
                prev.get("preview_image_url"), str
            ):
                preview_image_url = prev["preview_image_url"]
            updated_rows.append(
                _merge_post(
                    prev,
                    url,
                    lastmod,
                    slug,
                    title,
                    cached_at,
                    is_hub,
                    preview_image_url=preview_image_url,
                )
            )

    manifest["posts"] = updated_rows
    manifest["synced_at"] = _utc_now_iso()
    manifest["last_sync_error"] = last_err
    manifest["version"] = 1
    _save_manifest(wr, manifest)

    return build_blog_payload(workspace_root)


def build_blog_payload(workspace_root: Path) -> dict[str, Any]:
    """Return ``{ ok, posts, synced_at?, last_sync_error? }``."""
    wr = workspace_root.resolve()
    manifest = _load_manifest(wr)
    posts_raw = manifest.get("posts")
    rows: list[dict[str, Any]] = []
    html_dir = html_cache_dir(wr)

    if isinstance(posts_raw, list):
        for p in posts_raw:
            if not isinstance(p, dict):
                continue
            slug = p.get("slug")
            url = p.get("url")
            if not isinstance(slug, str) or not isinstance(url, str):
                continue
            sl = slug.strip().lower()
            if not _SAFE_SLUG_RE.match(sl):
                continue
            fp = html_dir / sl
            cached = fp.is_file()
            raw_pi = p.get("preview_image_url")
            preview_out: str | None = None
            if isinstance(raw_pi, str) and raw_pi.strip():
                preview_out = normalize_preview_image_url(raw_pi.strip())
            if preview_out is None and cached:
                preview_out = normalize_preview_image_url(
                    extract_og_image_from_html(fp.read_bytes())
                )
            row = {
                "url": url,
                "slug": sl,
                "lastmod": p.get("lastmod") if isinstance(p.get("lastmod"), str) else "",
                "title": p.get("title") if isinstance(p.get("title"), str) else None,
                "cached_at": p.get("cached_at")
                if isinstance(p.get("cached_at"), str)
                else None,
                "is_hub": bool(p.get("is_hub")),
                "cached": cached,
                "preview_image_url": preview_out,
            }
            rows.append(row)

    out: dict[str, Any] = {
        "ok": True,
        "posts": rows,
    }
    if isinstance(manifest.get("synced_at"), str):
        out["synced_at"] = manifest["synced_at"]
    err = manifest.get("last_sync_error")
    if isinstance(err, str) and err.strip():
        out["last_sync_error"] = err.strip()
    return out


def read_cached_html_with_base(workspace_root: Path, slug: str) -> tuple[bytes | None, str | None]:
    """Return cached HTML bytes with base href injected, or (None, error_code)."""
    sl = (slug or "").strip().lower()
    if not _SAFE_SLUG_RE.match(sl):
        return None, "invalid_slug"
    fp = html_cache_dir(workspace_root.resolve()) / sl
    try:
        fp = fp.resolve()
    except OSError:
        return None, "invalid_path"
    root = html_cache_dir(workspace_root.resolve()).resolve()
    try:
        fp.relative_to(root)
    except ValueError:
        return None, "path_escape"
    if not fp.is_file():
        return None, "not_found"
    raw = fp.read_bytes()
    return inject_base_href_after_head(raw), None
