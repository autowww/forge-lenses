"""Optional workspace-registry.json merged with defaults."""

from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any


DEFAULTS: dict[str, Any] = {
    "external_urls": {
        "handbook": "https://blueprints.forgesdlc.com/",
        "forge": "https://forgesdlc.com/",
    },
    "ignore_paths": [],
    "website_labels": {},
    "project_urls": {},
    "project_summaries": {},
    "overview_metrics_manual": {},
    "github_login": "",
    "actions": {},
}


def _normalize_actions(raw: Any) -> dict[str, Any]:
    if not isinstance(raw, dict):
        return {}
    out: dict[str, Any] = {}
    for site, spec in raw.items():
        if not isinstance(site, str) or not isinstance(spec, dict):
            continue
        site_actions: dict[str, Any] = {}
        for action_name, body in spec.items():
            if not isinstance(action_name, str) or not isinstance(body, dict):
                continue
            argv = body.get("argv")
            cwd_rel = body.get("cwd_relative", "")
            if not isinstance(argv, list) or not all(isinstance(x, str) for x in argv):
                continue
            if not isinstance(cwd_rel, str):
                continue
            if not argv:
                continue
            site_actions[action_name] = {
                "argv": list(argv),
                "cwd_relative": cwd_rel.strip() or ".",
            }
        if site_actions:
            out[site] = site_actions
    return out


def _merge_payload(merged: dict[str, Any], data: dict[str, Any]) -> None:
    if isinstance(data.get("external_urls"), dict):
        merged["external_urls"].update(data["external_urls"])
    if isinstance(data.get("ignore_paths"), list):
        merged["ignore_paths"] = [str(x) for x in data["ignore_paths"]]
    if isinstance(data.get("website_labels"), dict):
        merged["website_labels"].update(
            {str(k): str(v) for k, v in data["website_labels"].items()}
        )
    if isinstance(data.get("project_urls"), dict):
        merged["project_urls"].update(
            {str(k): str(v) for k, v in data["project_urls"].items()}
        )
    if isinstance(data.get("project_summaries"), dict):
        merged["project_summaries"].update(
            {str(k): str(v) for k, v in data["project_summaries"].items()}
        )
    if "overview_metrics_manual" in data:
        om = data.get("overview_metrics_manual")
        if isinstance(om, dict):
            merged["overview_metrics_manual"] = copy.deepcopy(om)
        else:
            merged["overview_metrics_manual"] = {}
    gl = data.get("github_login")
    if isinstance(gl, str) and gl.strip():
        merged["github_login"] = gl.strip()
    if "actions" in data:
        merged["actions"] = _normalize_actions(data.get("actions"))


def load_registry(
    lenses_repo_root: Path, workspace_root: Path | None = None
) -> dict[str, Any]:
    merged = copy.deepcopy(DEFAULTS)
    path = lenses_repo_root / "workspace-registry.json"
    if path.is_file():
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            data = {}
        if isinstance(data, dict):
            _merge_payload(merged, data)

    if workspace_root is not None:
        ws_path = workspace_root / "lenses-workspace-registry.json"
        if ws_path.is_file():
            try:
                ws_data = json.loads(ws_path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                ws_data = {}
            if isinstance(ws_data, dict):
                _merge_payload(merged, ws_data)

    return merged


def should_ignore_child(name: str, registry: dict[str, Any]) -> bool:
    return name in set(registry.get("ignore_paths") or [])
