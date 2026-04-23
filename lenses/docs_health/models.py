"""Domain shapes for Docs Health (DOCS-1+).

Serialized as JSON in API responses and under ``.lenses-local/docs-health/``.
"""

from __future__ import annotations

from typing import Any, TypedDict


class ProjectDocsContractMeta(TypedDict, total=False):
    """How the active contract was obtained."""

    source: str  # "repo_file" | "convention"
    contract_path: str | None  # e.g. forge/docs-contract.yaml
    legacy_path_used: str | None  # optional migration hint


class OwnershipMeta(TypedDict, total=False):
    team: str
    primary_contact: str


class ScopeMeta(TypedDict, total=False):
    repository: str
    module_paths: list[str]


class RequiredDocType(TypedDict, total=False):
    id: str
    label: str
    patterns: list[str]


class ProjectDocsContract(TypedDict, total=False):
    """Normalized documentation contract for one repository."""

    version: int
    doc_roots: list[str]
    skip_dir_names: list[str]
    max_file_bytes: int
    required_doc_types: list[RequiredDocType]
    required_files: list[str]
    readme_required_sections: list[str]
    require_adr: bool
    adr_globs: list[str]
    require_release_note: bool
    release_globs: list[str]
    require_architecture_diagram: bool
    architecture_scan_paths: list[str]
    ownership: OwnershipMeta
    scope: ScopeMeta
    _meta: ProjectDocsContractMeta


class DocsDocumentRecord(TypedDict, total=False):
    """One indexed markdown file."""

    path: str
    title: str
    headings: list[dict[str, Any]]  # {"level": int, "text": str}
    frontmatter: dict[str, Any]
    internal_links: list[str]
    doc_type: str
    knowledge_category: str  # docs | evidence | decisions | diagrams
    module_hint: str


class DocsLinkEdge(TypedDict, total=False):
    """Edge in the markdown link graph (relative paths when resolved)."""

    from_path: str
    to_path: str | None
    target_raw: str
    resolved: bool


class DocsInventorySnapshot(TypedDict, total=False):
    """Point-in-time inventory for scanners and UI."""

    id: str
    project: str
    created_at: str
    document_count: int
    documents: list[DocsDocumentRecord]
    link_graph: list[DocsLinkEdge]
    by_doc_type: dict[str, int]
    by_knowledge_category: dict[str, int]
    contract_snapshot_version: int | None


class DocsScanRunStub(TypedDict, total=False):
    """Placeholder until full scan pipeline is wired to inventory."""

    id: None
    status: str
    hint: str


def scan_run_stub() -> DocsScanRunStub:
    return {
        "id": None,
        "status": "pending_first_scan",
        "hint": "Quality scan uses the latest documentation index. Run “Index documentation” first if this project is new to Docs Health.",
    }


class DocsFinding(TypedDict, total=False):
    """Deterministic scan finding (DOCS-2)."""

    id: str
    title: str
    summary: str
    plain_language_summary: str
    category: str
    severity: str
    confidence: float
    scope: str
    affected_paths: list[str]
    affected_files: list[str]
    why_it_matters: str
    score_impact: int
    expected_score_impact: int
    fixability: str
    rule_code: str
    score_area: str
    suppressed: bool


class DocsFindingCluster(TypedDict, total=False):
    id: str
    label: str
    finding_ids: list[str]
    primary_category: str
    primary_severity: str
    expected_score_gain_if_cleared: int
    suggested_next: str
