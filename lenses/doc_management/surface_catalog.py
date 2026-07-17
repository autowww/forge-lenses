"""Hydration target surfaces and personas for Studio wizard pickers."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

_DEFAULT_SURFACES: list[dict[str, Any]] = [
    {
        "surface_id": "forgesdlc_blog",
        "label": "forgesdlc.com blog",
        "kind": "website",
        "repo": "forgesdlc",
        "relative_path": "blog",
    },
    {
        "surface_id": "forge_platform_architecture",
        "label": "Forge Platform handbook",
        "kind": "website",
        "repo": "forge-platform",
        "relative_path": "docs/standout",
    },
    {
        "surface_id": "blueprints_methodology",
        "label": "Blueprints methodology",
        "kind": "dual-wiki",
        "repo": "blueprints",
        "relative_path": "sdlc/methodologies/forge/standout",
    },
    {
        "surface_id": "forge_lcdl_docs",
        "label": "Forge LCDL handbook",
        "kind": "website",
        "repo": "forge-lcdl",
        "relative_path": "docs/guides/standout",
    },
    {
        "surface_id": "forge_lenses_docs",
        "label": "Forge Lenses docs",
        "kind": "tutorial",
        "repo": "forge-lenses",
        "relative_path": "docs/forge/standout",
    },
    {
        "surface_id": "forge_fleet_docs",
        "label": "Forge Fleet learn-101",
        "kind": "tutorial",
        "repo": "forge-fleet",
        "relative_path": "docs/learn-101/standout",
    },
]

_DEFAULT_PERSONAS: list[dict[str, Any]] = [
    {"persona_id": "c_level", "label": "C-level executive"},
    {"persona_id": "engineering_leader", "label": "Engineering leader"},
    {"persona_id": "architect", "label": "Architect"},
    {"persona_id": "practitioner", "label": "Practitioner"},
    {"persona_id": "operator", "label": "Operator"},
    {"persona_id": "agent", "label": "Agent"},
]


def _platform_root(workspace_root: Path) -> Path | None:
    p = workspace_root / "forge-platform"
    return p if p.is_dir() else None


def _load_personas_from_yaml(platform_root: Path) -> list[dict[str, Any]] | None:
    p = platform_root / "docs-governance" / "persona_journey_map.yaml"
    if not p.is_file():
        return None
    try:
        raw = yaml.safe_load(p.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError):
        return None
    if not isinstance(raw, dict):
        return None
    personas = raw.get("personas")
    if not isinstance(personas, list):
        return None
    out: list[dict[str, Any]] = []
    for row in personas:
        if not isinstance(row, dict):
            continue
        pid = str(row.get("persona_id") or "").strip()
        if not pid:
            continue
        out.append(
            {
                "persona_id": pid,
                "label": pid.replace("_", " ").title(),
                "main_question": row.get("main_question"),
            }
        )
    return out or None


def _load_surfaces_from_registry(platform_root: Path, workspace_root: Path) -> list[dict[str, Any]] | None:
    p = platform_root / "docs-governance" / "surface_registry.yaml"
    if not p.is_file():
        return None
    try:
        raw = yaml.safe_load(p.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError):
        return None
    if not isinstance(raw, dict):
        return None
    surfaces = raw.get("surfaces")
    if not isinstance(surfaces, list):
        return None
    out: list[dict[str, Any]] = []
    for row in surfaces:
        if not isinstance(row, dict):
            continue
        sid = str(row.get("surface_id") or "").strip()
        if not sid:
            continue
        rel = str(row.get("relative_path") or "").strip()
        repo = str(row.get("repo") or "").strip()
        abs_path = workspace_root / repo / rel if repo and rel else None
        out.append(
            {
                "surface_id": sid,
                "label": row.get("label") or sid,
                "kind": row.get("kind") or "website",
                "repo": repo,
                "relative_path": rel,
                "absolute_path": str(abs_path) if abs_path else None,
            }
        )
    return out or None


def catalog_payload(workspace_root: Path) -> dict[str, Any]:
    platform = _platform_root(workspace_root)
    personas = _DEFAULT_PERSONAS
    surfaces = _DEFAULT_SURFACES
    if platform is not None:
        loaded_p = _load_personas_from_yaml(platform)
        if loaded_p:
            personas = loaded_p
        loaded_s = _load_surfaces_from_registry(platform, workspace_root)
        if loaded_s:
            surfaces = loaded_s
    for s in surfaces:
        repo = str(s.get("repo") or "").strip()
        rel = str(s.get("relative_path") or "").strip()
        if repo and rel and not s.get("absolute_path"):
            s["absolute_path"] = str(workspace_root / repo / rel)
    return {"ok": True, "personas": personas, "surfaces": surfaces}


def resolve_surface_paths(workspace_root: Path, surface_ids: list[str]) -> dict[str, Path]:
    payload = catalog_payload(workspace_root)
    by_id = {str(s["surface_id"]): s for s in payload.get("surfaces") or [] if isinstance(s, dict)}
    out: dict[str, Path] = {}
    for sid in surface_ids:
        row = by_id.get(sid)
        if not row:
            continue
        ap = row.get("absolute_path")
        if ap:
            out[sid] = Path(ap)
    return out
