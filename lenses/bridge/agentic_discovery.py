"""Discover Forge agentic config, Cursor rules, and recipe files on disk."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

FORGE_CONFIG_REL = "forge/forge.config.yaml"
CURSOR_RULES_DIR = ".cursor/rules"


def _sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    h.update(p.read_bytes())
    return h.hexdigest()


def _try_load_yaml(text: str) -> dict[str, Any] | None:
    try:
        import yaml  # type: ignore[import-untyped]

        data = yaml.safe_load(text)
        return data if isinstance(data, dict) else None
    except Exception:
        return None


def discover_forge_config(workspace_root: Path) -> dict[str, Any]:
    """Parse ``forge/forge.config.yaml`` when present (requires PyYAML)."""
    root = workspace_root.resolve()
    p = root / FORGE_CONFIG_REL
    out: dict[str, Any] = {
        "ok": False,
        "rel_path": FORGE_CONFIG_REL,
        "present": False,
        "parse_error": None,
        "data": None,
        "active_versona_families": [],
        "active_disciplines": [],
    }
    if not p.is_file():
        return out
    out["present"] = True
    try:
        text = p.read_text(encoding="utf-8")
    except OSError as ex:
        out["parse_error"] = str(ex)
        return out
    data = _try_load_yaml(text)
    if data is None:
        out["parse_error"] = "yaml_parse_failed_or_missing_pyyaml"
        return out
    out["data"] = data
    out["ok"] = True
    versona = data.get("versona") if isinstance(data.get("versona"), dict) else {}
    families = versona.get("families") if isinstance(versona.get("families"), dict) else {}
    for k, v in families.items():
        if v is True:
            out["active_versona_families"].append(str(k))
    for block_name in ("product_disciplines", "engineering_disciplines", "cross_cutting"):
        block = versona.get(block_name) if isinstance(versona.get(block_name), dict) else {}
        for k, v in block.items():
            if v is True:
                out["active_disciplines"].append(str(k))
    return out


def list_cursor_rules(workspace_root: Path) -> list[dict[str, Any]]:
    root = workspace_root.resolve()
    d = root / CURSOR_RULES_DIR
    if not d.is_dir():
        return []
    rows: list[dict[str, Any]] = []
    for p in sorted(d.iterdir()):
        if not p.is_file():
            continue
        if p.suffix.lower() not in (".mdc", ".md"):
            continue
        rel = str(p.relative_to(root)).replace("\\", "/")
        try:
            st = p.stat()
            rows.append(
                {
                    "rel_path": rel,
                    "basename": p.name,
                    "size": st.st_size,
                    "mtime_ns": int(getattr(st, "st_mtime_ns", int(st.st_mtime * 1e9))),
                    "checksum_sha256": _sha256_file(p),
                }
            )
        except OSError:
            continue
    return rows


def discover_recipe_files(workspace_root: Path, globs: list[str]) -> list[dict[str, Any]]:
    root = workspace_root.resolve()
    seen: set[str] = set()
    rows: list[dict[str, Any]] = []
    for pattern in globs:
        base_part = pattern.split("**", 1)[0].rstrip("/") if "**" in pattern else ""
        if not base_part:
            continue
        base = root / base_part
        if not base.is_dir():
            continue
        pl = pattern.lower()
        exts: list[str] = []
        if pl.endswith("*.md") or pl.endswith(".md"):
            exts.append(".md")
        if "*.yaml" in pl or pl.endswith(".yaml"):
            exts.append(".yaml")
        if "*.yml" in pl or pl.endswith(".yml"):
            exts.append(".yml")
        if not exts:
            exts = [".md", ".yaml", ".yml"]
        for p in base.rglob("*"):
            if not p.is_file():
                continue
            if p.suffix.lower() not in exts:
                continue
            rel = str(p.relative_to(root)).replace("\\", "/")
            if rel in seen:
                continue
            seen.add(rel)
            try:
                st = p.stat()
                rows.append(
                    {
                        "rel_path": rel,
                        "size": st.st_size,
                        "mtime_ns": int(getattr(st, "st_mtime_ns", int(st.st_mtime * 1e9))),
                        "checksum_sha256": _sha256_file(p),
                    }
                )
            except OSError:
                continue
    rows.sort(key=lambda r: r["rel_path"])
    return rows


def build_rules_manifest(workspace_root: Path, reg: dict[str, Any]) -> dict[str, Any]:
    cfg = discover_forge_config(workspace_root)
    rules = list_cursor_rules(workspace_root)
    globs = list(reg.get("recipe_scan_globs") or [])
    recipes = discover_recipe_files(workspace_root, globs)
    basenames = {r["basename"] for r in rules}
    return {
        "ok": True,
        "forge_config": {"ok": cfg.get("ok"), "rel_path": cfg.get("rel_path"), "present": cfg.get("present")},
        "cursor_rules_count": len(rules),
        "cursor_rule_basenames": sorted(basenames),
        "recipe_file_count": len(recipes),
        "recipe_rel_paths": [r["rel_path"] for r in recipes],
        "generated_at_iso": __import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat(),
    }


def snapshot_manifest_json(manifest: dict[str, Any]) -> str:
    return json.dumps(manifest, separators=(",", ":"), sort_keys=True)
