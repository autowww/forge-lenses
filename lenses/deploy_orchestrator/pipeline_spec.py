"""Discover and validate ``forge/delivery-pipeline.yaml`` from workspace child repos."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import yaml
from jsonschema import Draft202012Validator

PIPELINE_REL = Path("forge") / "delivery-pipeline.yaml"
PIPELINES_DIR = Path("forge") / "pipelines"
SCHEMA_REL = Path("docs") / "schemas" / "delivery-pipeline.schema.json"
LENSES_REPO_ROOT = Path(__file__).resolve().parents[2]


def schema_path() -> Path:
    return LENSES_REPO_ROOT / SCHEMA_REL


def load_schema() -> dict[str, Any]:
    raw = json.loads(schema_path().read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError("invalid_schema")
    return raw


def discover_pipeline_paths(workspace_root: Path) -> dict[str, Path]:
    """Map project folder name → legacy default pipeline YAML path."""
    out: dict[str, Path] = {}
    root = workspace_root.resolve()
    if not root.is_dir():
        return out
    for child in sorted(root.iterdir()):
        if not child.is_dir():
            continue
        candidate = child / PIPELINE_REL
        if candidate.is_file():
            out[child.name] = candidate
    return out


def discover_pipelines(workspace_root: Path) -> dict[str, dict[str, Path]]:
    """Map project → pipeline_id → YAML path."""
    grouped: dict[str, dict[str, Path]] = {}
    root = workspace_root.resolve()
    if not root.is_dir():
        return grouped
    for child in sorted(root.iterdir()):
        if not child.is_dir():
            continue
        pipes: dict[str, Path] = {}
        legacy = child / PIPELINE_REL
        if legacy.is_file():
            pipes["default"] = legacy
        pipe_dir = child / PIPELINES_DIR
        if pipe_dir.is_dir():
            for yf in sorted(pipe_dir.glob("*.yaml")):
                pipes[yf.stem] = yf
        if pipes:
            grouped[child.name] = pipes
    return grouped


def parse_pipeline_yaml(path: Path) -> dict[str, Any]:
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError("pipeline_not_mapping")
    return raw


def validate_pipeline(doc: dict[str, Any], *, schema: dict[str, Any] | None = None) -> list[str]:
    sch = schema if schema is not None else load_schema()
    validator = Draft202012Validator(sch)
    errors = sorted(validator.iter_errors(doc), key=lambda e: list(e.path))
    return [e.message for e in errors]


def load_pipeline_for_project(
    workspace_root: Path,
    project: str,
    *,
    pipeline_id: str = "default",
) -> dict[str, Any]:
    grouped = discover_pipelines(workspace_root)
    rel = str(project or "").strip()
    pid = str(pipeline_id or "default")
    paths = grouped.get(rel) or {}
    path = paths.get(pid)
    if path is None and pid == "default":
        path = discover_pipeline_paths(workspace_root).get(rel)
    if path is None:
        return {"ok": False, "error": "pipeline_not_found", "project": rel, "pipeline_id": pid}
    try:
        doc = parse_pipeline_yaml(path)
    except (OSError, yaml.YAMLError, ValueError) as ex:
        return {"ok": False, "error": "parse_failed", "detail": str(ex)[:400], "project": rel, "pipeline_id": pid}
    errs = validate_pipeline(doc)
    if errs:
        return {
            "ok": False,
            "error": "schema_invalid",
            "project": rel,
            "pipeline_id": pid,
            "validation_errors": errs[:20],
        }
    return {
        "ok": True,
        "project": rel,
        "pipeline_id": pid,
        "path": str(path),
        "pipeline": doc,
    }


def environment_by_id(pipeline: dict[str, Any], env_id: str) -> dict[str, Any] | None:
    for row in pipeline.get("environments") or []:
        if isinstance(row, dict) and str(row.get("id") or "") == str(env_id):
            return row
    return None


def gates_for_environment(pipeline: dict[str, Any], env_id: str) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for row in pipeline.get("gates") or []:
        if isinstance(row, dict) and str(row.get("environment") or "") == str(env_id):
            out.append(row)
    return out
