"""HTML transforms for /local-site/ preview: <base href>, root-relative href/src rewrite, MIME hints."""

from __future__ import annotations

import html
import mimetypes
import posixpath
import re
from pathlib import Path
from typing import Final

# Root-relative href= or src= (same line, double or single quoted). Skip // and /local-site/.
_ATTR_ROOT_REL: Final[re.Pattern[str]] = re.compile(
    r'(?P<attr>\b(?:href|src)\s*=\s*)(?P<q>["\'])(?P<val>/[^"\'\s>]*)',
    re.IGNORECASE,
)

_LOCAL_SITE_TYPES: Final[dict[str, str]] = {
    ".html": "text/html; charset=utf-8",
    ".htm": "text/html; charset=utf-8",
    ".css": "text/css; charset=utf-8",
    ".js": "text/javascript; charset=utf-8",
    ".mjs": "text/javascript; charset=utf-8",
    ".svg": "image/svg+xml; charset=utf-8",
    ".json": "application/json; charset=utf-8",
    ".webmanifest": "application/manifest+json; charset=utf-8",
    ".map": "application/json; charset=utf-8",
    ".woff2": "font/woff2",
    ".woff": "font/woff",
    ".ttf": "font/ttf",
    ".otf": "font/otf",
    ".eot": "application/vnd.ms-fontobject",
    ".ico": "image/x-icon",
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".webp": "image/webp",
    ".gif": "image/gif",
    ".bmp": "image/bmp",
    ".txt": "text/plain; charset=utf-8",
    ".xml": "application/xml; charset=utf-8",
}


def content_type_for_local_site_file(path: Path) -> str:
    ext = path.suffix.lower()
    if ext in _LOCAL_SITE_TYPES:
        return _LOCAL_SITE_TYPES[ext]
    mime, _ = mimetypes.guess_type(str(path))
    return mime or "application/octet-stream"


def local_site_directory_url_path(request_path: str) -> str:
    """Directory URL path (always ends with /) for the current document under /local-site/…"""
    p = request_path.split("?", 1)[0].rstrip("/")
    if not p:
        return "/"
    pl = p.lower()
    if pl.endswith(".html") or pl.endswith(".htm"):
        d = posixpath.dirname(p)
        return d + "/" if not d.endswith("/") else d
    return p + "/"


def build_local_site_base_href(
    *,
    scheme: str,
    host: str,
    directory_url_path: str,
) -> str:
    """Absolute base URL for <base href>; directory_url_path must start with / and end with /."""
    d = directory_url_path if directory_url_path.endswith("/") else directory_url_path + "/"
    if not d.startswith("/"):
        d = "/" + d
    h = host.strip() or "127.0.0.1"
    s = (scheme or "http").lower()
    if s not in ("http", "https"):
        s = "http"
    return f"{s}://{h}{d}"


def _has_base_href(html_text: str) -> bool:
    return bool(re.search(r"<base\s+[^>]*\bhref\s*=", html_text, re.IGNORECASE))


def inject_base_and_rewrite_local_site_html(
    html_bytes: bytes,
    *,
    base_href: str,
    site_name: str,
) -> bytes:
    """Decode UTF-8 HTML, inject <base> if absent, rewrite root-relative href/src to /local-site/<site>/…"""
    try:
        text = html_bytes.decode("utf-8")
    except UnicodeDecodeError:
        return html_bytes

    prefix = f"/local-site/{site_name}/"

    def rewrite_attr(m: re.Match[str]) -> str:
        val = m.group("val")
        q = m.group("q")
        attr = m.group("attr")
        if val.startswith("//"):
            return m.group(0)
        if val.startswith("/local-site/"):
            return m.group(0)
        inner = val[1:] if val.startswith("/") else val
        if not inner:
            new_val = prefix
        else:
            new_val = prefix + inner
        return f"{attr}{q}{new_val}{q}"

    text = _ATTR_ROOT_REL.sub(rewrite_attr, text)

    if _has_base_href(text):
        return text.encode("utf-8")

    safe_href = html.escape(base_href, quote=False)
    base_tag = f'<base href="{safe_href}">\n'
    m = re.search(r"<head[^>]*>", text, re.IGNORECASE)
    if m:
        pos = m.end()
        cm = re.search(
            r'<meta\s+[^>]*charset\s*=\s*[^>]+>',
            text[pos : pos + 400],
            re.IGNORECASE,
        )
        if cm:
            pos = pos + cm.end()
        return (text[:pos] + base_tag + text[pos:]).encode("utf-8")
    return (base_tag + text).encode("utf-8")
