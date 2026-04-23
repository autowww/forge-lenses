"""On-disk artifacts for Docs Health sessions (patch JSON, diff preview, apply gate — never the live repo)."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from typing import Any

from lenses.docs_health import store
from lenses.docs_health.diff_util import unified_diff_preview


def session_artifacts_dir(workspace_root: Path, project_slug: str, session_id: str) -> Path:
    sid = str(session_id or "").strip().replace(os.sep, "_").replace("/", "_")
    if not sid or ".." in sid:
        raise ValueError("invalid_session_id")
    d = store.ensure_store_dir(workspace_root, project_slug) / "sessions" / sid / "artifacts"
    d.mkdir(parents=True, exist_ok=True)
    try:
        os.chmod(d, 0o700)
    except OSError:
        pass
    return d


def _sha256_text(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def write_proposed_patch_artifact(
    workspace_root: Path,
    project_slug: str,
    session_id: str,
    patch: dict[str, str],
    *,
    kind: str | None = None,
    scratch_write: dict[str, Any] | None = None,
) -> Path:
    """Persist proposed markdown patch under session artifacts (draft boundary)."""
    d = session_artifacts_dir(workspace_root, project_slug, session_id)
    content = str(patch.get("content") if patch.get("content") is not None else "")
    payload: dict[str, Any] = {
        "patch": patch,
        "kind": kind,
        "written_at": store.now_iso(),
        "sha256": _sha256_text(content),
        "scratch_write": scratch_write,
    }
    p = d / "proposed_patch.json"
    p.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    try:
        os.chmod(p, 0o600)
    except OSError:
        pass
    return p


def write_diff_preview_artifact(
    workspace_root: Path,
    project_slug: str,
    session_id: str,
    repo_root: Path,
    patch: dict[str, str],
) -> Path | None:
    """Unified diff preview (read-only old file from ``repo_root``)."""
    rel = str(patch.get("path") or "").strip()
    if not rel:
        return None
    text = unified_diff_preview(repo_root.resolve(), rel_path=rel, new_content=str(patch.get("content") or ""))
    d = session_artifacts_dir(workspace_root, project_slug, session_id)
    p = d / "diff_preview.patch"
    p.write_text(text, encoding="utf-8")
    try:
        os.chmod(p, 0o600)
    except OSError:
        pass
    return p


def write_patch_bundle_manifest(
    workspace_root: Path,
    project_slug: str,
    session_id: str,
    *,
    paths: list[str],
    scratch_root: str | None,
) -> Path:
    """Lightweight bundle descriptor (paths + scratch root) for UI / tooling."""
    d = session_artifacts_dir(workspace_root, project_slug, session_id)
    payload = {
        "paths": paths,
        "scratch_root": scratch_root,
        "written_at": store.now_iso(),
    }
    p = d / "patch_bundle.json"
    p.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    try:
        os.chmod(p, 0o600)
    except OSError:
        pass
    return p


def write_apply_ready_artifact(
    workspace_root: Path,
    project_slug: str,
    session_id: str,
    *,
    sha256: str,
    status: str = "pending_apply",
) -> Path:
    """Gate marker: apply step must read canonical patch + verify ``sha256``."""
    d = session_artifacts_dir(workspace_root, project_slug, session_id)
    payload = {
        "version": 1,
        "canonical_artifact": "proposed_patch.json",
        "sha256": sha256,
        "status": status,
        "created_at": store.now_iso(),
    }
    p = d / "apply_ready.json"
    p.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    try:
        os.chmod(p, 0o600)
    except OSError:
        pass
    return p


def mark_apply_consumed(
    workspace_root: Path,
    project_slug: str,
    session_id: str,
) -> None:
    p = session_artifacts_dir(workspace_root, project_slug, session_id) / "apply_ready.json"
    if not p.is_file():
        return
    try:
        raw = json.loads(p.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return
    if not isinstance(raw, dict):
        return
    raw["status"] = "applied"
    raw["consumed_at"] = store.now_iso()
    p.write_text(json.dumps(raw, indent=2, sort_keys=True), encoding="utf-8")


def write_discarded_marker(
    workspace_root: Path,
    project_slug: str,
    session_id: str,
    *,
    reason: str,
) -> Path:
    d = session_artifacts_dir(workspace_root, project_slug, session_id)
    p = d / "discarded.json"
    p.write_text(
        json.dumps({"reason": reason, "at": store.now_iso()}, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    try:
        os.chmod(p, 0o600)
    except OSError:
        pass
    return p


def load_proposed_patch_artifact(
    workspace_root: Path,
    project_slug: str,
    session_id: str,
) -> dict[str, Any] | None:
    p = session_artifacts_dir(workspace_root, project_slug, session_id) / "proposed_patch.json"
    if not p.is_file():
        return None
    try:
        raw = json.loads(p.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return raw if isinstance(raw, dict) else None


def list_artifact_manifest(workspace_root: Path, project_slug: str, session_id: str) -> list[dict[str, Any]]:
    """Lightweight manifest for Studio (paths relative to session artifact dir)."""
    d = session_artifacts_dir(workspace_root, project_slug, session_id)
    out: list[dict[str, Any]] = []
    for name in (
        "proposed_patch.json",
        "diff_preview.patch",
        "patch_bundle.json",
        "apply_ready.json",
        "discarded.json",
    ):
        p = d / name
        if p.is_file():
            try:
                st = p.stat()
                out.append({"name": name, "bytes": int(st.st_size), "updated_at": store.now_iso()})
            except OSError:
                continue
    return out


def load_apply_gate(workspace_root: Path, project_slug: str, session_id: str) -> dict[str, Any] | None:
    """``apply_ready.json`` payload if present."""
    p = session_artifacts_dir(workspace_root, project_slug, session_id) / "apply_ready.json"
    if not p.is_file():
        return None
    try:
        raw = json.loads(p.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return raw if isinstance(raw, dict) else None


def load_patch_for_apply(
    workspace_root: Path,
    project_slug: str,
    session_id: str,
    *,
    expected_sha256: str | None = None,
) -> dict[str, str] | None:
    """
    Load canonical patch for apply. Verifies ``sha256`` when ``expected_sha256`` or ``apply_ready.json`` supplies it.
    """
    data = load_proposed_patch_artifact(workspace_root, project_slug, session_id)
    if not data:
        return None
    patch = data.get("patch") if isinstance(data.get("patch"), dict) else None
    if not patch:
        return None
    content = str(patch.get("content") if patch.get("content") is not None else "")
    digest = _sha256_text(content)
    gate = load_apply_gate(workspace_root, project_slug, session_id)
    exp = expected_sha256 or (gate.get("sha256") if isinstance(gate, dict) else None)
    if isinstance(exp, str) and exp.strip() and exp.strip() != digest:
        return None
    if isinstance(data.get("sha256"), str) and data["sha256"].strip() and data["sha256"].strip() != digest:
        return None
    return {"path": str(patch.get("path") or "").strip(), "content": content}
