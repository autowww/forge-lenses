"""Normalize Doc Management intake: paste, zip, URL, blog cache → seed Markdown files."""

from __future__ import annotations

import html
import io
import re
import urllib.error
import urllib.request
import zipfile
from pathlib import Path
from typing import Any

from lenses.doc_management import session_store as store

_MANUAL_EXT = {".pdf", ".html", ".htm"}
_MD_EXT = {".md", ".markdown", ".txt"}


def _slugify(name: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    return slug or "seed"


def _strip_html_to_text(raw: str) -> str:
    text = re.sub(r"(?is)<script[^>]*>.*?</script>", " ", raw)
    text = re.sub(r"(?is)<style[^>]*>.*?</style>", " ", text)
    text = re.sub(r"(?is)<br\s*/?>", "\n", text)
    text = re.sub(r"(?is)</p>", "\n\n", text)
    text = re.sub(r"(?is)<h[1-6][^>]*>", "\n\n# ", text)
    text = re.sub(r"<[^>]+>", " ", text)
    text = html.unescape(text)
    text = re.sub(r"[ \t]+\n", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def normalize_text_intake(workspace_root: Path, session_id: str, text: str, *, name: str = "seed.md") -> dict[str, Any]:
    intake = store.intake_dir(workspace_root, session_id)
    fname = name if name.endswith(".md") else f"{name}.md"
    dest = intake / f"{_slugify(Path(fname).stem)}.md"
    dest.write_text(text.strip() + "\n", encoding="utf-8")
    return {"path": str(dest.relative_to(store.session_dir(workspace_root, session_id))), "name": dest.name, "status": "ready"}


def normalize_zip_intake(workspace_root: Path, session_id: str, zip_bytes: bytes) -> tuple[list[dict[str, Any]], list[str]]:
    intake = store.intake_dir(workspace_root, session_id)
    seeds: list[dict[str, Any]] = []
    manual: list[str] = []
    with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
        for info in zf.infolist():
            if info.is_dir():
                continue
            name = Path(info.filename).name
            if not name or name.startswith("."):
                continue
            ext = Path(name).suffix.lower()
            if ext in _MANUAL_EXT:
                manual.append(info.filename)
                continue
            if ext not in _MD_EXT:
                manual.append(info.filename)
                continue
            data = zf.read(info)
            try:
                text = data.decode("utf-8")
            except UnicodeDecodeError:
                manual.append(info.filename)
                continue
            dest = intake / (_slugify(Path(name).stem) + ".md")
            dest.write_text(text.strip() + "\n", encoding="utf-8")
            seeds.append(
                {
                    "path": str(dest.relative_to(store.session_dir(workspace_root, session_id))),
                    "name": dest.name,
                    "status": "ready",
                    "source_archive": info.filename,
                }
            )
    return seeds, manual


def normalize_url_intake(workspace_root: Path, session_id: str, url: str) -> dict[str, Any]:
    req = urllib.request.Request(url, headers={"User-Agent": "Forge-Lenses-DocManagement/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            raw = resp.read()
            ctype = resp.headers.get("Content-Type", "")
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        raise ValueError(f"url_fetch_failed: {exc}") from exc
    text: str
    status = "ready"
    if "html" in ctype.lower() or raw[:15].lower().startswith(b"<!doctype") or b"<html" in raw[:500].lower():
        text = _strip_html_to_text(raw.decode("utf-8", errors="replace"))
    else:
        try:
            text = raw.decode("utf-8")
        except UnicodeDecodeError:
            status = "needs_manual_seed"
            text = f"# URL intake\n\nSource: {url}\n\n(Binary content — manual seed required.)\n"
    slug = _slugify(url.split("/")[-1] or "url-seed")
    intake = store.intake_dir(workspace_root, session_id)
    dest = intake / f"{slug}.md"
    header = f"---\nsource_url: {url}\n---\n\n"
    dest.write_text(header + text.strip() + "\n", encoding="utf-8")
    return {
        "path": str(dest.relative_to(store.session_dir(workspace_root, session_id))),
        "name": dest.name,
        "status": status,
        "source_url": url,
    }


def normalize_blog_intake(workspace_root: Path, session_id: str, slug: str) -> dict[str, Any]:
    from lenses.forgesdlc_blog import read_cached_html_with_base

    data, err = read_cached_html_with_base(workspace_root, slug)
    if err or not data:
        raise ValueError(err or "blog_cache_missing")
    text = _strip_html_to_text(data)
    intake = store.intake_dir(workspace_root, session_id)
    dest = intake / f"{_slugify(slug)}.md"
    header = f"---\nsource_blog_slug: {slug}\nintake_source: blog\n---\n\n"
    dest.write_text(header + text + "\n", encoding="utf-8")
    return {
        "path": str(dest.relative_to(store.session_dir(workspace_root, session_id))),
        "name": dest.name,
        "status": "ready",
        "blog_slug": slug,
    }


def apply_intake_to_session(
    workspace_root: Path,
    session: dict[str, Any],
    *,
    intake_source: str,
    text: str | None = None,
    zip_bytes: bytes | None = None,
    url: str | None = None,
    blog_slug: str | None = None,
    display_name: str | None = None,
) -> dict[str, Any]:
    sid = str(session.get("id") or "")
    wizard = session.setdefault("wizard", {})
    if not isinstance(wizard, dict):
        wizard = {}
        session["wizard"] = wizard
    wizard["intake_source"] = intake_source
    seeds: list[dict[str, Any]] = []
    warnings: list[str] = []

    if intake_source == "paste":
        if not (text or "").strip():
            raise ValueError("missing_text")
        seeds.append(normalize_text_intake(workspace_root, sid, text or ""))
    elif intake_source == "zip":
        if not zip_bytes:
            raise ValueError("missing_zip")
        seeds, manual = normalize_zip_intake(workspace_root, sid, zip_bytes)
        if manual:
            warnings.extend([f"skipped_non_md:{p}" for p in manual])
        if not seeds:
            raise ValueError("zip_has_no_md_seeds")
    elif intake_source == "url":
        if not (url or "").strip():
            raise ValueError("missing_url")
        wizard["source_url"] = url.strip()
        seeds.append(normalize_url_intake(workspace_root, sid, url.strip()))
    elif intake_source == "blog":
        if not (blog_slug or "").strip():
            raise ValueError("missing_blog_slug")
        wizard["blog_slug"] = blog_slug.strip()
        seeds.append(normalize_blog_intake(workspace_root, sid, blog_slug.strip()))
    else:
        raise ValueError("unsupported_intake_source")

    session["intake"] = {"seeds": seeds, "warnings": warnings}
    if display_name:
        session["display_name"] = display_name
    store.append_event(
        session,
        {
            "type": "intake",
            "title": "Intake normalized",
            "body": f"{len(seeds)} seed(s) from {intake_source}",
            "seed_count": len(seeds),
        },
    )
    session["workflow"] = {"stage": "intake", "stages_completed": ["intake"]}
    store.save_session(workspace_root, session)
    return session
