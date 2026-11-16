"""Resolve ``forge/docs-contract.yaml`` (or convention defaults) for a repository."""

from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any

import yaml

PRIMARY_CONTRACT_REL = Path("forge") / "docs-contract.yaml"
LEGACY_CONTRACT_REL = Path("lenses-docs-contract.yaml")


def _default_required_doc_types() -> list[dict[str, Any]]:
    return [
        {"id": "readme", "label": "Project readme", "patterns": ["README.md", "Readme.md", "readme.md"]},
        {"id": "changelog", "label": "Release / changelog", "patterns": ["CHANGELOG.md", "CHANGELOG"]},
        {"id": "adr", "label": "Architecture decisions", "patterns": ["docs/decisions/*.md", "docs/adr/*.md", "adr/*.md"]},
        {
            "id": "architecture",
            "label": "Architecture overview",
            "patterns": ["docs/architecture.md", "docs/ARCHITECTURE.md"],
        },
        {"id": "readiness", "label": "Readiness notes", "patterns": ["docs/readiness*.md", "docs/release*.md"]},
    ]


def _default_contract_dict() -> dict[str, Any]:
    return {
        "version": 1,
        "doc_roots": [".", "docs"],
        "required_doc_types": _default_required_doc_types(),
        "required_files": ["README.md"],
        "readme_required_sections": ["Overview", "Getting started"],
        "require_adr": True,
        "adr_globs": ["docs/decisions/*.md", "docs/adr/*.md", "adr/*.md"],
        "require_release_note": True,
        "release_globs": ["CHANGELOG.md", "CHANGELOG", "docs/release*.md", "docs/readiness*.md"],
        "require_architecture_diagram": True,
        "architecture_scan_paths": ["README.md", "docs/architecture.md", "docs/README.md"],
        "ownership": {},
        "scope": {"repository": "", "module_paths": []},
        "skip_dir_names": [
            ".git",
            "node_modules",
            "__pycache__",
            ".venv",
            "venv",
            "dist",
            "build",
            "target",
            ".idea",
            ".vscode",
        ],
        "max_file_bytes": 400_000,
    }


def _flatten_required_patterns(required_doc_types: list[dict[str, Any]]) -> list[str]:
    out: list[str] = []
    for row in required_doc_types:
        if not isinstance(row, dict):
            continue
        for p in row.get("patterns") or []:
            ps = str(p).strip()
            if ps and ps not in out:
                out.append(ps)
    return out


def normalize_contract(base: dict[str, Any], *, repo_name: str) -> dict[str, Any]:
    """Ensure legacy scanner keys and scope defaults exist."""
    c = copy.deepcopy(base)
    rdts = c.get("required_doc_types")
    if not isinstance(rdts, list) or not rdts:
        c["required_doc_types"] = _default_required_doc_types()
    # Flatten first glob-free pattern per type into required_files if missing empty
    req_files = c.get("required_files")
    if not isinstance(req_files, list) or not req_files:
        acc: list[str] = []
        for row in c["required_doc_types"]:
            if not isinstance(row, dict):
                continue
            for pat in row.get("patterns") or []:
                p = str(pat).strip()
                if "*" in p or "?" in p or "[" in p:
                    continue
                if p.endswith(".md") or p == "CHANGELOG":
                    acc.append(p)
        c["required_files"] = acc or ["README.md"]
    own = c.get("ownership")
    if not isinstance(own, dict):
        c["ownership"] = {}
    sc = c.get("scope")
    if not isinstance(sc, dict):
        c["scope"] = {}
    if not str(c["scope"].get("repository") or "").strip():
        c["scope"]["repository"] = repo_name
    mod = c["scope"].get("module_paths")
    if not isinstance(mod, list):
        c["scope"]["module_paths"] = []
    meta = c.get("_meta")
    if not isinstance(meta, dict):
        c["_meta"] = {}
    return c


def _merge_yaml_into_base(base: dict[str, Any], loaded: dict[str, Any]) -> None:
    for k, v in loaded.items():
        if k in base and isinstance(base[k], dict) and isinstance(v, dict):
            merged = dict(base[k])
            merged.update(v)
            base[k] = merged
        else:
            base[k] = v


def load_project_docs_contract(repo_root: Path) -> dict[str, Any]:
    """Load YAML from disk when present; otherwise defaults only (no _meta)."""
    base = json.loads(json.dumps(_default_contract_dict()))
    primary = repo_root / PRIMARY_CONTRACT_REL
    legacy = repo_root / LEGACY_CONTRACT_REL
    path_used: Path | None = None
    if primary.is_file():
        path_used = primary
    elif legacy.is_file():
        path_used = legacy
    if path_used is None:
        return base
    try:
        raw = path_used.read_text(encoding="utf-8")
    except OSError:
        return base
    try:
        loaded = yaml.safe_load(raw)
    except yaml.YAMLError:
        return base
    if not isinstance(loaded, dict):
        return base
    _merge_yaml_into_base(base, loaded)
    return base


def resolve_project_docs_contract(repo_root: Path, *, project_slug: str) -> dict[str, Any]:
    """
    Full contract for API + scanners: merged file (if any), normalized, with ``_meta``.

    Preference: ``forge/docs-contract.yaml``, then legacy ``lenses-docs-contract.yaml``.
    """
    base = load_project_docs_contract(repo_root)
    primary = repo_root / PRIMARY_CONTRACT_REL
    legacy = repo_root / LEGACY_CONTRACT_REL
    meta: dict[str, Any] = {"source": "convention", "contract_path": None, "legacy_path_used": None}
    if primary.is_file():
        meta["source"] = "repo_file"
        meta["contract_path"] = str(PRIMARY_CONTRACT_REL).replace("\\", "/")
    elif legacy.is_file():
        meta["source"] = "repo_file"
        meta["contract_path"] = str(LEGACY_CONTRACT_REL).replace("\\", "/")
        meta["legacy_path_used"] = str(LEGACY_CONTRACT_REL).replace("\\", "/")
    out = normalize_contract(base, repo_name=project_slug)
    out["_meta"] = meta
    return out


def contract_status_payload(repo_root: Path, resolved: dict[str, Any]) -> dict[str, Any]:
    meta = resolved.get("_meta") if isinstance(resolved.get("_meta"), dict) else {}
    return {
        "mode": "configured" if meta.get("source") == "repo_file" else "default",
        "contract_path": meta.get("contract_path"),
        "uses_convention_defaults": meta.get("source") == "convention",
        "legacy_contract": bool(meta.get("legacy_path_used")),
    }
