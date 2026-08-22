"""Markdown inventory and link graph for Docs Health (DOCS-1)."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from datetime import datetime, timezone

from lenses.docs_health.scanner import LINK_RE


def split_frontmatter(text: str) -> tuple[dict[str, Any], str]:
    """Return (frontmatter dict, body). Supports a single YAML front matter block at start."""
    if not text.startswith("---"):
        return {}, text
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return {}, text
    close = None
    for i in range(1, min(len(lines), 400)):
        if lines[i].strip() == "---":
            close = i
            break
    if close is None:
        return {}, text
    raw_fm = "\n".join(lines[1:close])
    body = "\n".join(lines[close + 1 :])
    try:
        import yaml  # noqa: PLC0415

        data = yaml.safe_load(raw_fm)
    except Exception:
        data = None
    if isinstance(data, dict):
        return data, body if body.startswith("\n") else ("\n" + body if body else body)
    return {}, text


def _headings_list(body: str) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for m in re.finditer(r"^(#{1,6})\s+(.+)$", body, re.MULTILINE):
        out.append({"level": len(m.group(1)), "text": m.group(2).strip()})
    return out


def _first_title(body: str, fallback: str) -> str:
    for m in re.finditer(r"^#\s+(.+)$", body, re.MULTILINE):
        return m.group(1).strip()
    return fallback


def _resolve_internal(repo_root: Path, from_file: Path, target: str) -> Path | None:
    t = target.strip()
    if not t or t.startswith(("#", "http://", "https://", "mailto:")):
        return None
    t = t.split("#", 1)[0].strip()
    if not t:
        return None
    base = from_file.parent
    cand = (base / t).resolve()
    try:
        cand.relative_to(repo_root.resolve())
    except ValueError:
        return None
    return cand


def classify_doc_type(rel_posix: str) -> str:
    p = rel_posix.replace("\\", "/").lower()
    name = Path(p).name
    if name in ("readme.md", "readme.markdown"):
        return "readme"
    if "changelog" in name or p.endswith("/changelog"):
        return "changelog"
    if "/decisions/" in f"/{p}/" or "/adr/" in f"/{p}/" or p.startswith("adr/"):
        return "adr"
    if "architecture" in p or "system-design" in p:
        return "architecture"
    if "readiness" in p or "release-note" in p or "/release/" in f"/{p}/":
        return "readiness"
    if p.startswith("docs/") or "/docs/" in f"/{p}/":
        return "guide"
    return "other"


def knowledge_category_for(
    rel_posix: str,
    doc_type: str,
    body: str,
) -> str:
    p = rel_posix.replace("\\", "/").lower()
    if doc_type == "adr" or "/decisions/" in f"/{p}/":
        return "decisions"
    if "evidence" in p or "assay" in p or "readiness" in p or doc_type == "readiness":
        return "evidence"
    if "```mermaid" in body.lower() or re.search(r"!\[[^\]]*]\([^)]+\.(svg|png)\)", body, re.I):
        return "diagrams"
    return "docs"


def module_hint(rel_posix: str) -> str:
    parts = Path(rel_posix.replace("\\", "/")).parts
    if len(parts) >= 2 and parts[0] in ("docs", "src", "lib", "packages"):
        return f"{parts[0]}/{parts[1]}" if len(parts) > 1 else parts[0]
    if len(parts) >= 1:
        return parts[0]
    return ""


def build_inventory_snapshot(
    repo_root: Path,
    *,
    project_slug: str,
    contract: dict[str, Any],
) -> dict[str, Any]:
    """Walk markdown under contract doc_roots and build snapshot + link graph."""
    from lenses.docs_health.scanner import _iter_markdown_files  # noqa: PLC0415

    repo_root = repo_root.resolve()
    skip = set(str(x) for x in (contract.get("skip_dir_names") or []) if str(x).strip())
    doc_roots = [str(x).strip() for x in (contract.get("doc_roots") or ["."]) if str(x).strip()]
    max_bytes = int(contract.get("max_file_bytes") or 400_000)
    files = _iter_markdown_files(repo_root, doc_roots, skip, max_bytes)

    documents: list[dict[str, Any]] = []
    edges: list[dict[str, Any]] = []
    by_dt: dict[str, int] = {}
    by_kc: dict[str, int] = {}

    for fp in files:
        rel = str(fp.relative_to(repo_root)).replace("\\", "/")
        try:
            raw = fp.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        fm, body = split_frontmatter(raw)
        title = str(fm.get("title") or "").strip() or _first_title(body, fp.stem)
        headings = _headings_list(body)
        internal: list[str] = []
        for m in LINK_RE.finditer(body):
            tgt = m.group(1).strip()
            if tgt.startswith(("http://", "https://", "mailto:", "#")):
                continue
            internal.append(tgt)
            cand = _resolve_internal(repo_root, fp, tgt)
            edges.append(
                {
                    "from_path": rel,
                    "to_path": str(cand.relative_to(repo_root)).replace("\\", "/") if cand and cand.is_file() else None,
                    "target_raw": tgt,
                    "resolved": bool(cand and cand.is_file()),
                }
            )
        dt = classify_doc_type(rel)
        kc = knowledge_category_for(rel, dt, body)
        by_dt[dt] = by_dt.get(dt, 0) + 1
        by_kc[kc] = by_kc.get(kc, 0) + 1
        documents.append(
            {
                "path": rel,
                "title": title,
                "headings": headings,
                "frontmatter": fm,
                "internal_links": internal,
                "doc_type": dt,
                "knowledge_category": kc,
                "module_hint": module_hint(rel),
            }
        )

    import uuid  # noqa: PLC0415

    return {
        "id": uuid.uuid4().hex,
        "project": project_slug,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "document_count": len(documents),
        "documents": documents,
        "link_graph": edges,
        "by_doc_type": by_dt,
        "by_knowledge_category": by_kc,
        "contract_snapshot_version": int(contract.get("version") or 1),
    }


