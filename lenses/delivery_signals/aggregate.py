"""Build ``GET /api/delivery/overview`` payload from workspace scan + local fixtures."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from lenses.delivery_signals.feature_flag import experimental_delivery_signals_enabled
from lenses.delivery_signals.local_signals_store import (
    load_demo_fixture,
    read_local_delivery_signals,
)


def _lenses_package_root() -> Path:
    return Path(__file__).resolve().parent.parent


def _truthy_env(name: str) -> bool:
    raw = (os.environ.get(name) or "").strip().lower()
    return raw in ("1", "true", "yes", "on")


def _normalize_repo_fixture(obj: Any) -> dict[str, Any] | None:
    if not isinstance(obj, dict):
        return None
    out: dict[str, Any] = {}
    for key in ("ci_provider", "default_branch"):
        v = obj.get(key)
        if isinstance(v, str) and v.strip():
            out[key] = v.strip()
    for key in ("workflows", "trace_links", "environments", "releases"):
        v = obj.get(key)
        if isinstance(v, list):
            out[key] = v
    return out


def build_delivery_overview_payload(
    *,
    workspace_root: Path,
    scan_state: dict[str, Any],
    force_flag: bool | None = None,
) -> dict[str, Any]:
    """Stable JSON for Studio and classic consumers.

    ``force_flag`` supports tests (override env).
    """
    enabled = (
        experimental_delivery_signals_enabled() if force_flag is None else bool(force_flag)
    )
    children = scan_state.get("children")
    if not isinstance(children, list):
        children = []

    git_count = sum(1 for c in children if isinstance(c, dict) and c.get("is_git"))

    if not enabled:
        return {
            "ok": True,
            "schema_version": 1,
            "feature_enabled": False,
            "provider_kind": "disabled",
            "resolved_at": scan_state.get("resolved_at"),
            "workspace_summary": {
                "child_count": len(children),
                "git_repo_count": git_count,
            },
            "repos": [],
            "hints": [
                "Delivery signal overlays are off. Default is on; you likely set "
                "LENSES_EXPERIMENTAL_DELIVERY_SIGNALS=0. Remove it or set =1, then restart Lenses.",
                "When enabled, use `.lenses-local/delivery-signals.json` for CI runs, PR links, and "
                "environment rows (local-first; remote adapters plug in later).",
            ],
        }

    local_doc = read_local_delivery_signals(workspace_root)
    fixture_map: dict[str, Any] = {}
    if isinstance(local_doc, dict) and isinstance(local_doc.get("repos"), dict):
        fixture_map = dict(local_doc["repos"])
    elif _truthy_env("LENSES_DELIVERY_SIGNALS_SEED_DEMO"):
        demo = load_demo_fixture(_lenses_package_root())
        if isinstance(demo, dict) and isinstance(demo.get("repos"), dict):
            fixture_map = dict(demo["repos"])

    provider_kind = "local_fixture" if fixture_map else "scan_only"
    hints: list[str] = []
    if not fixture_map:
        hints.append(
            "No `.lenses-local/delivery-signals.json` found — workspace scan lists repositories only. "
            "Copy `lenses/fixtures/delivery-signals.demo.json` into `.lenses-local/delivery-signals.json` "
            "or set LENSES_DELIVERY_SIGNALS_SEED_DEMO=1 for a demo overlay."
        )

    repos_out: list[dict[str, Any]] = []
    for c in children:
        if not isinstance(c, dict):
            continue
        name = str(c.get("name") or "").strip()
        if not name:
            continue
        git = c.get("git") if isinstance(c.get("git"), dict) else {}
        row: dict[str, Any] = {
            "project": name,
            "is_git": bool(c.get("is_git")),
            "git_head_short": git.get("head_short") if isinstance(git.get("head_short"), str) else "",
            "git_branch": git.get("branch") if isinstance(git.get("branch"), str) else "",
            "origin_url": git.get("origin_url") if isinstance(git.get("origin_url"), str) else "",
            "workflows": [],
            "trace_links": [],
            "environments": [],
            "releases": [],
            "data_sources": ["workspace_scan"],
        }
        fix = fixture_map.get(name)
        norm = _normalize_repo_fixture(fix)
        if norm:
            row["data_sources"] = ["workspace_scan", "local_fixture"]
            for k, v in norm.items():
                row[k] = v
        repos_out.append(row)

    return {
        "ok": True,
        "schema_version": 1,
        "feature_enabled": True,
        "provider_kind": provider_kind,
        "resolved_at": scan_state.get("resolved_at"),
        "workspace_summary": {
            "child_count": len(children),
            "git_repo_count": git_count,
        },
        "repos": repos_out,
        "hints": hints,
    }
