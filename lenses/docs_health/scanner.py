"""Deterministic markdown documentation scanners (DOCS-2)."""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

LINK_RE = re.compile(r"\[[^\]]*]\(([^)]+)\)")
HEADING_RE = re.compile(r"^#{1,6}\s+(.+)$", re.MULTILINE)
PLACEHOLDER_RE = re.compile(
    r"\b(TODO|TBD|FIXME|PLACEHOLDER|\.\.\.|XXX)\b",
    re.IGNORECASE,
)
# Very short body after heading (stub section)
STUB_SECTION_RE = re.compile(
    r"^#{2,6}\s+(.+)$\s*\n\s*(\n|$)(?=#{|\Z)",
    re.MULTILINE,
)

# Weights for headline score (must sum to 1.0 for documentation)
SCORE_WEIGHTS: dict[str, float] = {
    "required_files": 0.22,
    "sections": 0.18,
    "links": 0.20,
    "traceability": 0.18,
    "diagrams": 0.12,
    "quality": 0.10,
}

FINDING_AREA: dict[str, str] = {
    "missing_file": "required_files",
    "required_doc_type": "required_files",
    "readme_section": "sections",
    "empty_section": "sections",
    "architecture_section": "diagrams",
    "broken_md_link": "links",
    "broken_inventory_link": "links",
    "placeholder_language": "quality",
    "adr_missing": "traceability",
    "release_note_missing": "traceability",
    "architecture_diagram": "diagrams",
    "scope_doc_drift": "quality",
}


@dataclass
class Finding:
    """Single deterministic docs finding (serialized as DocsFinding)."""

    id: str
    title: str
    summary: str
    category: str
    severity: str
    confidence: float
    scope: str
    affected_paths: list[str]
    why_it_matters: str
    score_impact: int
    fixability: str
    rule_code: str
    suppressed: bool = False

    def expected_score_gain(self) -> int:
        """Points recovered toward 100 if this finding is cleared (non-negative)."""
        return max(0, -int(self.score_impact))

    def as_dict(self) -> dict[str, Any]:
        area = FINDING_AREA.get(self.rule_code, "quality")
        return {
            "id": self.id,
            "title": self.title,
            "summary": self.summary,
            "plain_language_summary": self.summary,
            "category": self.category,
            "severity": self.severity,
            "confidence": self.confidence,
            "scope": self.scope,
            "affected_paths": list(self.affected_paths),
            "affected_files": list(self.affected_paths),
            "why_it_matters": self.why_it_matters,
            "score_impact": self.score_impact,
            "expected_score_impact": self.expected_score_gain(),
            "fixability": self.fixability,
            "rule_code": self.rule_code,
            "score_area": area,
            "suppressed": self.suppressed,
        }


def _fid(parts: str) -> str:
    return hashlib.sha256(parts.encode("utf-8")).hexdigest()[:16]


def _iter_markdown_files(
    repo_root: Path,
    doc_roots: list[str],
    skip_names: set[str],
    max_bytes: int,
) -> list[Path]:
    out: list[Path] = []
    seen: set[str] = set()
    root_res = repo_root.resolve()
    for root_rel in doc_roots:
        base = (repo_root / root_rel).resolve()
        try:
            base.relative_to(root_res)
        except ValueError:
            continue
        if not base.is_dir():
            continue
        for p in base.rglob("*.md"):
            try:
                p.relative_to(root_res)
            except ValueError:
                continue
            if any(part in skip_names for part in p.parts):
                continue
            try:
                if p.stat().st_size > max_bytes:
                    continue
            except OSError:
                continue
            key = str(p.resolve())
            if key in seen:
                continue
            seen.add(key)
            out.append(p)
    out.sort(key=lambda x: str(x).lower())
    return out


def _glob_contract(repo_root: Path, pattern: str) -> list[Path]:
    """Glob from repo root; pattern uses forward slashes."""
    pat = pattern.strip().replace("\\", "/").lstrip("/")
    if not pat:
        return []
    try:
        return [p for p in repo_root.glob(pat) if p.is_file()]
    except OSError:
        return []


def _match_required_doc_type(repo_root: Path, patterns: Iterable[str]) -> bool:
    for pat in patterns:
        ps = str(pat).strip()
        if not ps:
            continue
        if ps == "CHANGELOG":
            if (repo_root / "CHANGELOG").is_file() or (repo_root / "CHANGELOG").is_dir():
                return True
            continue
        hits = _glob_contract(repo_root, ps)
        if hits:
            return True
        # Single-file path without glob
        if "*" not in ps and "?" not in ps and "[" not in ps:
            if (repo_root / ps).is_file():
                return True
    return False


def _readme_path(repo_root: Path) -> Path | None:
    for name in ("README.md", "Readme.md", "readme.md"):
        p = repo_root / name
        if p.is_file():
            return p
    return None


def _section_titles(text: str) -> set[str]:
    titles: set[str] = set()
    for m in HEADING_RE.finditer(text):
        titles.add(m.group(1).strip().casefold())
    return titles


def _has_architecture_signal(text: str) -> bool:
    if "```mermaid" in text.lower():
        return True
    for m in re.finditer(r"!\[[^\]]*]\(([^)]+)\)", text):
        u = m.group(1).strip().lower()
        if u.endswith((".svg", ".png", ".jpg", ".jpeg", ".webp")):
            return True
    return False


def _resolve_link(repo_root: Path, from_file: Path, target: str) -> Path | None:
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


def _architecture_doc_body(repo_root: Path) -> tuple[str, str | None]:
    """Return (combined text for diagram scan, primary arch doc path)."""
    for rel in ("docs/architecture.md", "docs/ARCHITECTURE.md", "docs/README.md"):
        p = repo_root / rel
        if p.is_file():
            try:
                return p.read_text(encoding="utf-8", errors="replace"), rel
            except OSError:
                return "", rel
    return "", None


def _stub_headings(text: str) -> list[str]:
    """Headings immediately followed by blank / EOF (likely empty section)."""
    bad: list[str] = []
    for m in STUB_SECTION_RE.finditer(text):
        title = m.group(1).strip()
        if title:
            bad.append(title)
    return bad


def run_deterministic_scan(
    repo_root: Path,
    contract: dict[str, Any],
    *,
    inventory_snapshot: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Return inventory, findings, clusters, score, and inspectable score math."""
    repo_root = repo_root.resolve()
    skip = set(str(x) for x in (contract.get("skip_dir_names") or []) if str(x).strip())
    doc_roots = [str(x).strip() for x in (contract.get("doc_roots") or ["."]) if str(x).strip()]
    max_bytes = int(contract.get("max_file_bytes") or 400_000)

    md_files = _iter_markdown_files(repo_root, doc_roots, skip, max_bytes)
    inventory_paths = [str(p.relative_to(repo_root)) for p in md_files]

    findings: list[Finding] = []
    seen_link_keys: set[str] = set()

    scope_label = "repository"
    sc = contract.get("scope")
    if isinstance(sc, dict) and str(sc.get("repository") or "").strip():
        scope_label = f"repository:{sc.get('repository')}"

    # Required explicit files
    for rel in contract.get("required_files") or []:
        rel_s = str(rel).strip()
        if not rel_s:
            continue
        p = repo_root / rel_s
        if not p.is_file():
            sev = "critical" if rel_s.replace("\\", "/").lower().endswith("readme.md") else "major"
            findings.append(
                Finding(
                    id=_fid(f"missing_file|{rel_s}"),
                    title=f"Missing required document: {rel_s}",
                    summary=f"The documentation contract expects `{rel_s}` at the repository root.",
                    category="missing_file",
                    severity=sev,
                    confidence=1.0,
                    scope=scope_label,
                    affected_paths=[rel_s],
                    why_it_matters="Onboarding and audits rely on a predictable doc spine.",
                    score_impact=-10,
                    fixability="draft_only",
                    rule_code="missing_file",
                )
            )

    # Required doc types (patterns)
    for row in contract.get("required_doc_types") or []:
        if not isinstance(row, dict):
            continue
        rid = str(row.get("id") or "").strip() or "doc_type"
        label = str(row.get("label") or rid).strip()
        pats = [str(x) for x in (row.get("patterns") or []) if str(x).strip()]
        if not pats:
            continue
        if _match_required_doc_type(repo_root, pats):
            continue
        findings.append(
            Finding(
                id=_fid(f"required_doc_type|{rid}"),
                title=f"Missing required documentation: {label}",
                summary=f"No file matched the contract patterns for “{label}” ({', '.join(pats[:3])}{'…' if len(pats) > 3 else ''}).",
                category="missing_file",
                severity="major",
                confidence=1.0,
                scope=scope_label,
                affected_paths=[pats[0] if pats else rid],
                why_it_matters="Checklist gaps make it unclear where canonical specs live.",
                score_impact=-8,
                fixability="draft_only",
                rule_code="required_doc_type",
            )
        )

    readme = _readme_path(repo_root)
    readme_text = ""
    if readme and readme.is_file():
        try:
            readme_text = readme.read_text(encoding="utf-8", errors="replace")
        except OSError:
            readme_text = ""

    for sec in contract.get("readme_required_sections") or []:
        label = str(sec).strip()
        if not label:
            continue
        if not readme:
            continue
        if label.casefold() not in _section_titles(readme_text):
            findings.append(
                Finding(
                    id=_fid(f"readme_section|{label}"),
                    title=f"README missing “{label}” section",
                    summary=f"Add a heading such as `## {label}` with a short, accurate description.",
                    category="structure",
                    severity="minor",
                    confidence=1.0,
                    scope=scope_label,
                    affected_paths=["README.md"],
                    why_it_matters="Readers skim headings first; missing sections hide important context.",
                    score_impact=-5,
                    fixability="draft_only",
                    rule_code="readme_section",
                )
            )

    # Empty stub sections in README
    if readme_text:
        for heading in _stub_headings(readme_text):
            findings.append(
                Finding(
                    id=_fid(f"empty_section|readme|{heading}"),
                    title=f"README section may be empty: {heading}",
                    summary=f"The heading “{heading}” is followed by little or no content.",
                    category="structure",
                    severity="minor",
                    confidence=0.7,
                    scope=scope_label,
                    affected_paths=["README.md"],
                    why_it_matters="Empty sections look like unfinished templates.",
                    score_impact=-3,
                    fixability="draft_only",
                    rule_code="empty_section",
                )
            )

    # Broken relative markdown links (from files)
    for fp in md_files:
        try:
            body = fp.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        rel_self = str(fp.relative_to(repo_root))
        for m in LINK_RE.finditer(body):
            target = m.group(1).strip()
            if target.startswith(("http://", "https://", "mailto:")):
                continue
            if target.startswith("#"):
                continue
            cand = _resolve_link(repo_root, fp, target)
            if cand is None:
                continue
            is_doc_link = target.endswith(".md") or "/docs/" in target.replace("\\", "/").lower()
            if not is_doc_link:
                continue
            key = f"{rel_self}|{target}"
            if key in seen_link_keys:
                continue
            if not cand.is_file():
                seen_link_keys.add(key)
                findings.append(
                    Finding(
                        id=_fid(f"broken_link|{rel_self}|{target}"),
                        title="Broken documentation link",
                        summary=f"Link target `{target}` does not exist (from `{rel_self}`).",
                        category="link_integrity",
                        severity="major",
                        confidence=1.0,
                        scope=scope_label,
                        affected_paths=[rel_self, target],
                        why_it_matters="Broken links break navigation and erode trust in the knowledge base.",
                        score_impact=-8,
                        fixability="manual",
                        rule_code="broken_md_link",
                    )
                )

    # Inventory link graph (deterministic, may catch more edges)
    if inventory_snapshot and isinstance(inventory_snapshot.get("link_graph"), list):
        for edge in inventory_snapshot["link_graph"]:
            if not isinstance(edge, dict):
                continue
            if edge.get("resolved") is True:
                continue
            raw = str(edge.get("target_raw") or "").strip()
            if raw.startswith(("#", "http://", "https://", "mailto:")):
                continue
            from_p = str(edge.get("from_path") or "")
            key = f"{from_p}|{raw}"
            if key in seen_link_keys:
                continue
            seen_link_keys.add(key)
            findings.append(
                Finding(
                    id=_fid(f"invlink|{from_p}|{raw}"),
                    title="Broken link (from documentation index)",
                    summary=f"Indexed link `{raw}` from `{from_p}` does not resolve to a file.",
                    category="link_integrity",
                    severity="major",
                    confidence=1.0,
                    scope=scope_label,
                    affected_paths=[from_p, raw],
                    why_it_matters="The documentation index shows navigation paths readers cannot follow.",
                    score_impact=-6,
                    fixability="manual",
                    rule_code="broken_inventory_link",
                )
            )

    # Placeholders
    for fp in md_files:
        try:
            body = fp.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        rel_self = str(fp.relative_to(repo_root))
        if PLACEHOLDER_RE.search(body):
            findings.append(
                Finding(
                    id=_fid(f"placeholder|{rel_self}"),
                    title="Incomplete or placeholder wording",
                    summary="Remove TODO/TBD/placeholder phrasing or replace it with finished prose.",
                    category="placeholder",
                    severity="minor",
                    confidence=0.85,
                    scope=scope_label,
                    affected_paths=[rel_self],
                    why_it_matters="Placeholders signal unfinished work to readers and auditors.",
                    score_impact=-4,
                    fixability="draft_only",
                    rule_code="placeholder_language",
                )
            )

    # ADR / decisions
    if contract.get("require_adr"):
        adr_patterns = [str(x) for x in (contract.get("adr_globs") or []) if str(x).strip()]
        adr_hits: list[Path] = []
        for pat in adr_patterns:
            adr_hits.extend(_glob_contract(repo_root, pat))
        adr_hits = list({str(p.resolve()): p for p in adr_hits}.values())
        if not adr_hits:
            findings.append(
                Finding(
                    id=_fid("adr_missing"),
                    title="No architecture decision records found",
                    summary="Add lightweight ADR stubs under docs/decisions/ or docs/adr/ (see contract globs).",
                    category="decision_trace",
                    severity="major",
                    confidence=1.0,
                    scope=scope_label,
                    affected_paths=["docs/decisions/"],
                    why_it_matters="Decisions without records are hard to defend during reviews and handoffs.",
                    score_impact=-10,
                    fixability="ticket_only",
                    rule_code="adr_missing",
                )
            )

    # Release / readiness notes
    if contract.get("require_release_note"):
        rel_patterns = [str(x) for x in (contract.get("release_globs") or []) if str(x).strip()]
        rel_hits: list[Path] = []
        for pat in rel_patterns:
            rel_hits.extend(_glob_contract(repo_root, pat))
        rel_hits = list({str(p.resolve()): p for p in rel_hits}.values())
        if not rel_hits:
            findings.append(
                Finding(
                    id=_fid("release_missing"),
                    title="No release or readiness note found",
                    summary="Add CHANGELOG.md or docs/readiness notes so shipping status is visible.",
                    category="release_readiness",
                    severity="minor",
                    confidence=0.9,
                    scope=scope_label,
                    affected_paths=["CHANGELOG.md"],
                    why_it_matters="Release notes connect engineering work to customer-facing communication.",
                    score_impact=-5,
                    fixability="ticket_only",
                    rule_code="release_note_missing",
                )
            )

    # Architecture diagram signal (README + configured paths + architecture doc)
    if contract.get("require_architecture_diagram"):
        scan_paths = [str(x) for x in (contract.get("architecture_scan_paths") or ["README.md"]) if str(x)]
        combined = ""
        arch_path: str | None = None
        for sp in scan_paths:
            p = repo_root / sp
            if p.is_file():
                try:
                    combined += p.read_text(encoding="utf-8", errors="replace")
                except OSError:
                    pass
        arch_body, arch_primary = _architecture_doc_body(repo_root)
        if arch_body:
            combined += "\n" + arch_body
            arch_path = arch_primary

        has_signal = bool(combined.strip()) and _has_architecture_signal(combined)
        if combined.strip() and not has_signal:
            apaths = [x for x in scan_paths[:3] if x]
            if arch_path:
                apaths.append(arch_path)
            findings.append(
                Finding(
                    id=_fid("diagram_missing"),
                    title="Architecture diagram not detected in key docs",
                    summary="Add a diagram (Mermaid block or SVG/PNG image link) in README or docs/architecture.md.",
                    category="diagram",
                    severity="minor",
                    confidence=0.75,
                    scope=scope_label,
                    affected_paths=apaths or ["README.md"],
                    why_it_matters="Visual architecture anchors onboarding and reduces misalignment.",
                    score_impact=-6,
                    fixability="draft_only",
                    rule_code="architecture_diagram",
                )
            )
        # Explicit architecture doc section when file exists
        if arch_body and arch_path:
            titles_cf = _section_titles(arch_body)
            if not any(t in titles_cf for t in ("architecture", "system overview", "context")):
                findings.append(
                    Finding(
                        id=_fid("arch_section_missing"),
                        title="Architecture doc missing overview section",
                        summary="Add a heading such as `## Architecture` with narrative or a diagram.",
                        category="diagram",
                        severity="minor",
                        confidence=0.65,
                        scope=scope_label,
                        affected_paths=[arch_path],
                        why_it_matters="A labeled architecture section helps readers find the system view quickly.",
                        score_impact=-4,
                        fixability="draft_only",
                        rule_code="architecture_section",
                    )
                )

    # Scope drift: module_paths in contract vs repo tree
    if isinstance(sc, dict):
        for mod in sc.get("module_paths") or []:
            ms = str(mod).strip().strip("/")
            if not ms or ".." in ms:
                continue
            mp = (repo_root / ms).resolve()
            try:
                mp.relative_to(repo_root)
            except ValueError:
                continue
            if not mp.exists():
                findings.append(
                    Finding(
                        id=_fid(f"scope_drift|{ms}"),
                        title=f"Documentation scope lists missing path: {ms}",
                        summary=f"The contract `scope.module_paths` entry `{ms}` does not exist in this checkout.",
                        category="scope_drift",
                        severity="minor",
                        confidence=0.95,
                        scope=scope_label,
                        affected_paths=[ms, "forge/docs-contract.yaml"],
                        why_it_matters="Stale scope lists mislead readers about where code or docs live.",
                        score_impact=-5,
                        fixability="manual",
                        rule_code="scope_doc_drift",
                    )
                )

    # --- Score math (inspectable) ---
    area_penalties: dict[str, int] = {k: 0 for k in SCORE_WEIGHTS}
    for f in findings:
        area = FINDING_AREA.get(f.rule_code, "quality")
        if area not in area_penalties:
            area = "quality"
        area_penalties[area] += f.score_impact  # negative values

    sub_scores: dict[str, dict[str, Any]] = {}
    for area, w in SCORE_WEIGHTS.items():
        raw = 100 + area_penalties.get(area, 0)
        val = max(0, min(100, int(round(raw))))
        sub_scores[area] = {
            "weight": w,
            "value": val,
            "penalty_sum": area_penalties.get(area, 0),
        }

    weighted = sum(sub_scores[a]["value"] * SCORE_WEIGHTS[a] for a in SCORE_WEIGHTS)
    headline = int(round(max(0, min(100, weighted))))

    # Legacy sum-based score for comparison
    sum_score = 100 + sum(int(f.score_impact) for f in findings)
    sum_score = max(0, min(100, sum_score))

    potential_gain = sum(f.expected_score_gain() for f in findings)
    potential_total = max(0, min(100, headline + potential_gain))

    clusters = _cluster_findings([f.as_dict() for f in findings])

    return {
        "ok": True,
        "inventory": {
            "markdown_files": inventory_paths,
            "markdown_file_count": len(inventory_paths),
        },
        "findings": [f.as_dict() for f in findings],
        "clusters": clusters,
        "score": {
            "value": headline,
            "scale_max": 100,
            "finding_count": len(findings),
            "sub_scores": sub_scores,
            "weights": dict(SCORE_WEIGHTS),
            "formula": (
                "headline = round(sum(sub_score[area] * weight[area])) for areas "
                "(required_files, sections, links, traceability, diagrams, quality); "
                "each sub_score = clamp(100 + sum(score_impact) for findings mapped to that area, 0, 100). "
                "Also reported: sum_based_score for diagnostics."
            ),
            "sum_based_score": sum_score,
            "potential_value_if_all_findings_cleared": potential_total,
            "potential_delta_if_resolved": potential_total - headline,
            "total_expected_recovery_points": potential_gain,
        },
    }


def _cluster_findings(findings: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Group by severity + category (readable clusters)."""
    buckets: dict[str, list[str]] = {}
    for f in findings:
        cat = str(f.get("category") or "general")
        sev = str(f.get("severity") or "info")
        key = f"{sev}|{cat}"
        buckets.setdefault(key, []).append(str(f.get("id", "")))

    out: list[dict[str, Any]] = []
    for key in sorted(buckets.keys()):
        sev, cat = key.split("|", 1)
        ids = [i for i in buckets[key] if i]
        gain = 0
        id_set = set(ids)
        for f in findings:
            if str(f.get("id")) in id_set:
                gain += int(f.get("expected_score_impact") or 0)
        label = f"{sev.title()} · {cat.replace('_', ' ')}"
        cid = _fid(f"cluster|{key}")
        out.append(
            {
                "id": cid,
                "label": label,
                "finding_ids": ids,
                "primary_category": cat,
                "primary_severity": sev,
                "expected_score_gain_if_cleared": gain,
                "suggested_next": "Review findings below, then open Master mode or a remediation session when ready.",
            }
        )
    return out
