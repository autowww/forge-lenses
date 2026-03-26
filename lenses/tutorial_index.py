"""Resolve forge-autodoc handbook trees under each workspace child (see ``list_child_handbooks``).

- ``tutorial/index.html`` — optional sync target after ``build-fa-tutorials.sh`` (e.g. forge-lenses).
- ``tutorials/index.html`` — typical ``output_dir`` at repo root (e.g. aw3).
- ``lenses/tutorials/index.html`` — forge-lenses build output when not rsynced to ``tutorial/``.

The dashboard route ``/tutorials`` (global index) is separate from the local-site prefix
``/local-site/<repo>/tutorials/…`` (plural), which serves forge-autodoc HTML output.

URL prefixes ``/local-site/<repo>/tutorial/…`` and ``…/tutorials/…`` are implemented in ``serve.py``.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

# Relative paths used in dashboard links to handbook root pages.
TUTORIAL_INDEX_REL_PATH = "tutorial/index.html"
REPO_TUTORIALS_INDEX_REL_PATH = "tutorials/index.html"

_TUTORIAL_PREFIX = re.compile(r"^tutorial(?:/(.*))?$", re.I)
_REPO_TUTORIALS_PREFIX = re.compile(r"^tutorials(?:/(.*))?$", re.I)


@dataclass(frozen=True)
class HandbookRef:
    """One built handbook under a workspace child (tutorial sync dir or tutorials output)."""

    kind: Literal["tutorial", "tutorials"]
    index_path: Path
    local_site_rel: str
    label_default: str


def resolve_child_tutorial_index_file(child: Path) -> Path | None:
    """Return ``<child>/tutorial/index.html`` when it exists and stays under ``child``."""
    try:
        child = child.resolve()
    except OSError:
        return None
    if not child.is_dir():
        return None
    candidate = (child / "tutorial" / "index.html").resolve()
    try:
        candidate.relative_to(child)
    except ValueError:
        return None
    return candidate if candidate.is_file() else None


def resolve_repo_tutorials_root(child: Path) -> Path | None:
    """
    Directory that backs URL prefix ``tutorials/``: prefer ``child/tutorials``,
    else ``child/lenses/tutorials`` when it contains ``index.html``.
    """
    try:
        child = child.resolve()
    except OSError:
        return None
    if not child.is_dir():
        return None
    for rel in ("tutorials", Path("lenses") / "tutorials"):
        base = (child / rel).resolve()
        try:
            base.relative_to(child)
        except ValueError:
            continue
        if base.is_dir() and (base / "index.html").is_file():
            return base
    return None


def list_child_handbooks(child: Path) -> list[HandbookRef]:
    """Ordered list: ``tutorial`` first (if present), then ``tutorials`` (if present)."""
    out: list[HandbookRef] = []
    tut = resolve_child_tutorial_index_file(child)
    if tut:
        out.append(
            HandbookRef(
                kind="tutorial",
                index_path=tut,
                local_site_rel=TUTORIAL_INDEX_REL_PATH,
                label_default="Tutorial",
            )
        )
    repo_root = resolve_repo_tutorials_root(child)
    if repo_root:
        idx = (repo_root / "index.html").resolve()
        if idx.is_file():
            out.append(
                HandbookRef(
                    kind="tutorials",
                    index_path=idx,
                    local_site_rel=REPO_TUTORIALS_INDEX_REL_PATH,
                    label_default="Engineer handbook",
                )
            )
    return out


def tutorial_url_tail_matches(rel: str) -> bool:
    """True if normalized relative URL path is ``tutorial`` or ``tutorial/…``."""
    s = (rel or "").strip().replace("\\", "/").lstrip("/")
    return bool(_TUTORIAL_PREFIX.match(s))


def repo_tutorials_url_tail_matches(rel: str) -> bool:
    """True if normalized relative URL path is ``tutorials`` or ``tutorials/…``."""
    s = (rel or "").strip().replace("\\", "/").lstrip("/")
    return bool(_REPO_TUTORIALS_PREFIX.match(s))


def resolve_tutorial_site_file(child: Path, rel: str) -> Path | None:
    """
    Map ``rel`` (must match ``tutorial`` or ``tutorial/…``) to a file under
    ``<child>/tutorial/``. Rejects ``..`` in the tail. Default empty tail → ``index.html``.
    """
    s = (rel or "").strip().replace("\\", "/").lstrip("/")
    m = _TUTORIAL_PREFIX.match(s)
    if not m:
        return None
    try:
        child = child.resolve()
    except OSError:
        return None
    tut_base = (child / "tutorial").resolve()
    if not tut_base.is_dir():
        return None
    try:
        tut_base.relative_to(child)
    except ValueError:
        return None
    tail = (m.group(1) or "").strip()
    if not tail:
        tail = "index.html"
    if ".." in tail.split("/"):
        return None
    candidate = (tut_base / tail).resolve()
    try:
        candidate.relative_to(tut_base)
    except ValueError:
        return None
    return candidate if candidate.is_file() else None


def resolve_repo_tutorials_site_file(child: Path, rel: str) -> Path | None:
    """
    Map ``rel`` matching ``tutorials`` or ``tutorials/…`` to a file under
    ``resolve_repo_tutorials_root(child)``. Default empty tail → ``index.html``.
    """
    s = (rel or "").strip().replace("\\", "/").lstrip("/")
    m = _REPO_TUTORIALS_PREFIX.match(s)
    if not m:
        return None
    base = resolve_repo_tutorials_root(child)
    if base is None:
        return None
    tail = (m.group(1) or "").strip()
    if not tail:
        tail = "index.html"
    if ".." in tail.split("/"):
        return None
    candidate = (base / tail).resolve()
    try:
        candidate.relative_to(base)
    except ValueError:
        return None
    return candidate if candidate.is_file() else None


def handbook_link_label_from_pages(
    pages: Any, local_site_rel: str, default_label: str
) -> str:
    """Title from Firebase ``pages`` when ``path`` matches ``local_site_rel``; else ``default_label``."""
    if not isinstance(pages, list):
        return default_label
    want = local_site_rel.lower().replace("\\", "/")
    for p in pages:
        if not isinstance(p, dict):
            continue
        rel = str(p.get("path", "")).replace("\\", "/").strip()
        if rel.lower() == want:
            lab = str(p.get("label", "")).strip()
            return lab if lab else default_label
    return default_label


def tutorial_link_label_from_pages(pages: Any) -> str:
    """Title/h1 label when ``tutorial/index.html`` is listed; else ``Tutorial``."""
    return handbook_link_label_from_pages(pages, TUTORIAL_INDEX_REL_PATH, "Tutorial")


def repo_tutorials_link_label_from_pages(pages: Any) -> str:
    """Title when ``tutorials/index.html`` is listed; else ``Engineer handbook``."""
    return handbook_link_label_from_pages(
        pages, REPO_TUTORIALS_INDEX_REL_PATH, "Engineer handbook"
    )
