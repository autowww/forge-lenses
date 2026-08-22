"""
Search markdown in the **project Git repo** (workspace child) for excerpts relevant to remediation findings.

Deterministic: keyword overlap from finding text + rule-specific terms, path proximity to affected files,
and bounded walks of ``doc_roots`` from the docs contract — no LLM calls.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

_MAX_CANDIDATE_PATHS = 120
_MAX_RANKED_FILES = 14
_MAX_EXCERPT_CHARS = 1_000
_MAX_READ_BYTES = 400_000

# Extra retrieval terms per rule — improves recall for policy-style constraints (e.g. diagram format).
_RULE_EXTRA_TERMS: dict[str, tuple[str, ...]] = {
    "architecture_diagram": ("diagram", "mermaid", "architecture", "svg", "png", "image", "visual", "figure"),
    "architecture_section": ("architecture", "overview", "section", "system"),
    "adr_missing": ("adr", "decision", "record", "decisions"),
    "broken_inventory_link": ("link", "href", "inventory", "broken"),
    "scope_doc_drift": ("scope", "module", "path", "directory"),
    "placeholder_language": ("placeholder", "todo", "fixme", "lorem"),
    "release_note_missing": ("release", "changelog", "readiness"),
}

_WELL_KNOWN_ROOT_MD = (
    "README.md",
    "Readme.md",
    "readme.md",
    "CONTRIBUTING.md",
    "CODE_OF_CONDUCT.md",
    "SECURITY.md",
    "GOVERNANCE.md",
    "docs/README.md",
    "docs/readme.md",
    "docs/contributing.md",
)


def _truncate(s: str, n: int) -> str:
    t = (s or "").strip()
    if len(t) <= n:
        return t
    return t[: n - 1] + "…"


def _tokenize_for_terms(s: str) -> set[str]:
    out: set[str] = set()
    for w in re.split(r"[^\w]+", s.lower()):
        if len(w) >= 3:
            out.add(w)
    return out


def collect_query_terms(findings: list[dict[str, Any]]) -> set[str]:
    terms: set[str] = set()
    for f in findings:
        rc = str(f.get("rule_code") or "").strip()
        if rc:
            terms.add(rc.lower())
            for part in rc.replace("-", "_").split("_"):
                if len(part) >= 3:
                    terms.add(part.lower())
            for extra in _RULE_EXTRA_TERMS.get(rc, ()):
                terms.add(extra.lower())
        for key in ("title", "summary", "plain_language_summary", "category", "why_it_matters"):
            terms |= _tokenize_for_terms(str(f.get(key) or ""))
    # Generic policy / guardrail vocabulary
    terms |= {
        "forbidden",
        "prohibited",
        "disallowed",
        "must",
        "must not",
        "policy",
        "guideline",
        "convention",
        "diagram",
        "mermaid",
    }
    return {t for t in terms if len(t) >= 2}


def _merge_skip_dirs(contract: dict[str, Any]) -> set[str]:
    base = {
        ".git",
        "node_modules",
        "__pycache__",
        ".venv",
        "venv",
        "dist",
        "build",
        "target",
        ".idea",
    }
    raw = contract.get("skip_dir_names") if isinstance(contract.get("skip_dir_names"), list) else []
    for x in raw:
        s = str(x).strip()
        if s:
            base.add(s)
    return base


def _path_skips_hidden(p: Path, skip_parts: set[str]) -> bool:
    for part in p.parts:
        if part in skip_parts:
            return True
        if part.startswith(".") and part not in (".", "..") and part != ".github":
            return True
    return False


def _collect_candidate_files(repo_root: Path, findings: list[dict[str, Any]], contract: dict[str, Any]) -> list[Path]:
    root = repo_root.resolve()
    skip_parts = _merge_skip_dirs(contract)
    doc_roots = contract.get("doc_roots") if isinstance(contract.get("doc_roots"), list) else None
    if not doc_roots:
        doc_roots = [".", "docs"]

    out: list[Path] = []
    seen: set[str] = set()

    def add(p: Path) -> None:
        try:
            rp = p.resolve()
            rp.relative_to(root)
        except ValueError:
            return
        if not rp.is_file() or rp.suffix.lower() != ".md":
            return
        if _path_skips_hidden(rp, skip_parts):
            return
        try:
            if rp.stat().st_size > _MAX_READ_BYTES:
                return
        except OSError:
            return
        key = str(rp)
        if key not in seen:
            seen.add(key)
            out.append(rp)

    # Affected paths: same file, siblings, parent folder
    for f in findings:
        for ap in f.get("affected_paths") or f.get("affected_files") or []:
            rel = str(ap).strip().replace("\\", "/")
            if not rel or ".." in rel or rel.startswith(("/", "\\")):
                continue
            p = root / rel
            if p.is_file() and p.suffix.lower() == ".md":
                add(p)
            elif p.is_dir():
                try:
                    for ch in sorted(p.glob("*.md"))[:28]:
                        add(ch)
                except OSError:
                    pass
            else:
                par = p.parent
                if par.is_dir():
                    try:
                        for ch in sorted(par.glob("*.md"))[:18]:
                            add(ch)
                    except OSError:
                        pass

    for rel in _WELL_KNOWN_ROOT_MD:
        add(root / rel)

    gh = root / ".github"
    if gh.is_dir():
        try:
            for ch in sorted(gh.glob("*.md"))[:24]:
                add(ch)
        except OSError:
            pass

    # Bounded walk under doc_roots
    for dr in doc_roots:
        drs = str(dr).strip().lstrip("/")
        if not drs or ".." in drs:
            continue
        base = root / drs
        if not base.is_dir():
            continue
        try:
            for p in base.rglob("*.md"):
                if len(out) >= _MAX_CANDIDATE_PATHS:
                    break
                if _path_skips_hidden(p, skip_parts):
                    continue
                add(p)
        except OSError:
            continue
        if len(out) >= _MAX_CANDIDATE_PATHS:
            break

    return out[:_MAX_CANDIDATE_PATHS]


def _score_text(text: str, terms: set[str]) -> int:
    if not text or not terms:
        return 0
    tl = text.lower()
    s = 0
    for t in terms:
        if len(t) < 2:
            continue
        s += tl.count(t.lower())
    return s


def _excerpt_for_file(text: str, terms: set[str]) -> tuple[str, list[str]]:
    """Return excerpt and which query terms matched in the excerpt (for UI)."""
    lines = text.splitlines()
    if not lines:
        return "", []
    best_i = 0
    best_sc = -1
    for i, line in enumerate(lines):
        sc = _score_text(line, terms)
        if sc > best_sc:
            best_sc = sc
            best_i = i
    if best_sc <= 0:
        chunk = "\n".join(lines[: min(40, len(lines))])
        tl = chunk.lower()
        matched = sorted({t for t in terms if len(t) > 2 and t.lower() in tl})[:12]
        return _truncate(chunk, _MAX_EXCERPT_CHARS), matched

    lo = max(0, best_i - 14)
    hi = min(len(lines), best_i + 16)
    chunk = "\n".join(lines[lo:hi])
    tl = chunk.lower()
    matched = sorted({t for t in terms if len(t) > 2 and t.lower() in tl})[:16]
    return _truncate(chunk, _MAX_EXCERPT_CHARS), matched


def build_repo_md_policy_context(
    repo_root: Path,
    findings: list[dict[str, Any]],
    *,
    contract: dict[str, Any],
) -> dict[str, Any]:
    """
    Rank markdown files in ``repo_root`` by relevance to the given findings; return top excerpts.

    This supports guardrail discovery: e.g. a ``docs/style.md`` that forbids Mermaid surfaces here when
    findings mention diagrams and the file contains "mermaid" / policy language.
    """
    terms = collect_query_terms(findings)
    if not terms:
        sc0 = contract.get("scope") if isinstance(contract.get("scope"), dict) else {}
        return {
            "repository_label": str(sc0.get("repository") or "").strip() or None,
            "query_terms": [],
            "hits": [],
            "scanned_file_count": 0,
            "note": "No query terms derived from findings.",
        }

    candidates = _collect_candidate_files(repo_root, findings, contract)
    scored: list[tuple[int, Path]] = []
    for p in candidates:
        try:
            raw = p.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        if len(raw.encode("utf-8", errors="replace")) > _MAX_READ_BYTES:
            continue
        sc = _score_text(raw, terms)
        if sc > 0:
            scored.append((sc, p))
    scored.sort(key=lambda x: (-x[0], str(x[1]).lower()))

    hits: list[dict[str, Any]] = []
    for sc, p in scored[:_MAX_RANKED_FILES]:
        rel = str(p.resolve().relative_to(repo_root.resolve())).replace("\\", "/")
        try:
            raw = p.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        excerpt, match_terms = _excerpt_for_file(raw, terms)
        hits.append(
            {
                "path": rel,
                "relevance_score": sc,
                "excerpt": excerpt,
                "match_terms": match_terms,
            }
        )

    scope = contract.get("scope") if isinstance(contract.get("scope"), dict) else {}
    repo_label = str(scope.get("repository") or "").strip() or None

    # Always surface directly affected .md files first (path relevance), even with low term overlap.
    hit_paths = {str(h.get("path") or "") for h in hits}
    priority: list[dict[str, Any]] = []
    for f in findings:
        for ap in f.get("affected_paths") or f.get("affected_files") or []:
            rel = str(ap).strip().replace("\\", "/")
            if not rel.lower().endswith(".md") or ".." in rel or rel in hit_paths:
                continue
            p = repo_root / rel
            try:
                p.resolve().relative_to(repo_root.resolve())
            except ValueError:
                continue
            if not p.is_file():
                continue
            try:
                if p.stat().st_size > _MAX_READ_BYTES:
                    continue
                raw = p.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            ex, mt = _excerpt_for_file(raw, terms)
            priority.append(
                {
                    "path": rel,
                    "relevance_score": _score_text(raw, terms) + 3,  # small boost vs unrelated files
                    "excerpt": ex,
                    "match_terms": mt,
                    "source": "affected_path",
                }
            )
            hit_paths.add(rel)
            if len(priority) >= 8:
                break

    prio_paths = {str(x.get("path") or "") for x in priority}
    merged = priority + [h for h in hits if str(h.get("path") or "") not in prio_paths]
    merged = merged[:_MAX_RANKED_FILES]

    return {
        "repository_label": repo_label,
        "query_terms": sorted(terms)[:48],
        "hits": merged,
        "scanned_file_count": len(candidates),
        "ranked_file_count": len(scored),
        "note": (
            "Excerpts from Markdown files in this project repository, ranked by overlap with finding keywords "
            "and paths under doc_roots (deterministic — complements ``forge/docs-contract.yaml`` and team policies)."
        ),
    }
