"""JSON-shaped responses for Blueprints Wizard HTTP handlers."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from lenses.blueprints_wizard.payload_validate import validate_wizard_payload_paths
from lenses.blueprints_wizard.session_store import (
    create_session,
    list_session_summaries,
    load_session,
    save_session_replace,
    validate_session_id,
)


def parse_session_path(path: str) -> str | None:
    """
    If path is /api/blueprints/wizard/session/<id> with a single segment id, return id.
    """
    prefix = "/api/blueprints/wizard/session/"
    if not path.startswith(prefix):
        return None
    rest = path[len(prefix) :].lstrip("/")
    if not rest or "/" in rest:
        return None
    return rest


def parse_session_refine_path(path: str) -> str | None:
    """If path is /api/blueprints/wizard/session/<id>/refine, return session id."""
    prefix = "/api/blueprints/wizard/session/"
    if not path.startswith(prefix):
        return None
    rest = path[len(prefix) :].strip("/")
    parts = rest.split("/")
    if len(parts) != 2 or parts[1] != "refine":
        return None
    sid = parts[0]
    if not validate_session_id(sid):
        return None
    return sid


def parse_session_create_repo_path(path: str) -> str | None:
    """If path is /api/blueprints/wizard/session/<id>/create-repo, return session id."""
    prefix = "/api/blueprints/wizard/session/"
    if not path.startswith(prefix):
        return None
    rest = path[len(prefix) :].strip("/")
    parts = rest.split("/")
    if len(parts) != 2 or parts[1] != "create-repo":
        return None
    sid = parts[0]
    if not validate_session_id(sid):
        return None
    return sid


def parse_session_interpret_path(path: str) -> str | None:
    """If path is /api/blueprints/wizard/session/<id>/interpret, return session id."""
    prefix = "/api/blueprints/wizard/session/"
    if not path.startswith(prefix):
        return None
    rest = path[len(prefix) :].strip("/")
    parts = rest.split("/")
    if len(parts) != 2 or parts[1] != "interpret":
        return None
    sid = parts[0]
    if not validate_session_id(sid):
        return None
    return sid


def post_refine_session(workspace_root: Path, session_id: str, body: dict[str, Any]) -> dict[str, Any]:
    from lenses.blueprints_wizard.refine import refine_foundation_brief

    return refine_foundation_brief(workspace_root, session_id, body)


def post_interpret_session(workspace_root: Path, session_id: str, body: dict[str, Any]) -> dict[str, Any]:
    from lenses.blueprints_wizard.interpretation_service import interpret_wizard_session

    return interpret_wizard_session(workspace_root, session_id, body)


def post_create_session(workspace_root: Path) -> dict[str, Any]:
    sid = create_session(workspace_root)
    return {"ok": True, "session_id": sid}


def get_sessions_list(workspace_root: Path) -> dict[str, Any]:
    return {"ok": True, "sessions": list_session_summaries(workspace_root)}


def get_session(workspace_root: Path, session_id: str) -> dict[str, Any]:
    if not validate_session_id(session_id):
        return {"ok": False, "error": "invalid_session_id"}
    doc = load_session(workspace_root, session_id)
    if doc is None:
        return {"ok": False, "error": "not_found"}
    return {"ok": True, "session": doc.to_dict()}


def put_session(workspace_root: Path, session_id: str, body: dict[str, Any]) -> dict[str, Any]:
    from lenses.blueprints_wizard.schemas import WizardSessionDocument

    if not validate_session_id(session_id):
        return {"ok": False, "error": "invalid_session_id"}
    parsed = WizardSessionDocument.from_dict(body)
    if parsed is None:
        return {"ok": False, "error": "invalid_session"}
    ok_path, err_path = validate_wizard_payload_paths(workspace_root, parsed)
    if not ok_path:
        return {"ok": False, "error": err_path}
    ok, err = save_session_replace(workspace_root, session_id, parsed.to_dict())
    if not ok:
        return {"ok": False, "error": err or "save_failed"}
    return {"ok": True}


def post_create_repo(
    workspace_root: Path,
    session_id: str,
    body: dict[str, Any],
) -> dict[str, Any]:
    from lenses.blueprints_wizard.github_create import post_create_repo as _post

    return _post(workspace_root, session_id, body)


def parse_session_clarify_suggest_path(path: str) -> str | None:
    """If path is /api/blueprints/wizard/session/<id>/clarify-suggest, return session id."""
    prefix = "/api/blueprints/wizard/session/"
    if not path.startswith(prefix):
        return None
    rest = path[len(prefix) :].strip("/")
    parts = rest.split("/")
    if len(parts) != 2 or parts[1] != "clarify-suggest":
        return None
    sid = parts[0]
    if not validate_session_id(sid):
        return None
    return sid


def post_clarify_suggest_session(
    workspace_root: Path,
    session_id: str,
    body: dict[str, Any],
) -> dict[str, Any]:
    from lenses.blueprints_wizard.clarification_llm import suggest_clarification_questions

    return suggest_clarification_questions(workspace_root, session_id, body)


def parse_session_generate_artifacts_path(path: str) -> str | None:
    """If path is /api/blueprints/wizard/session/<id>/generate-artifacts, return session id."""
    prefix = "/api/blueprints/wizard/session/"
    if not path.startswith(prefix):
        return None
    rest = path[len(prefix) :].strip("/")
    parts = rest.split("/")
    if len(parts) != 2 or parts[1] != "generate-artifacts":
        return None
    sid = parts[0]
    if not validate_session_id(sid):
        return None
    return sid


def parse_session_artifact_review_path(path: str) -> str | None:
    """If path is /api/blueprints/wizard/session/<id>/artifact-review, return session id."""
    prefix = "/api/blueprints/wizard/session/"
    if not path.startswith(prefix):
        return None
    rest = path[len(prefix) :].strip("/")
    parts = rest.split("/")
    if len(parts) != 2 or parts[1] != "artifact-review":
        return None
    sid = parts[0]
    if not validate_session_id(sid):
        return None
    return sid


def post_generate_artifacts(
    workspace_root: Path,
    session_id: str,
    body: dict[str, Any],
) -> dict[str, Any]:
    from lenses.blueprints_wizard.artifact_generation_service import generate_artifacts

    return generate_artifacts(workspace_root, session_id, body)


def post_artifact_review(
    workspace_root: Path,
    session_id: str,
    body: dict[str, Any],
) -> dict[str, Any]:
    from lenses.blueprints_wizard.artifact_generation_service import apply_artifact_review

    return apply_artifact_review(workspace_root, session_id, body)


def parse_session_artifact_export_path(path: str) -> str | None:
    """If path is /api/blueprints/wizard/session/<id>/artifact-export, return session id."""
    prefix = "/api/blueprints/wizard/session/"
    if not path.startswith(prefix):
        return None
    rest = path[len(prefix) :].strip("/")
    parts = rest.split("/")
    if len(parts) != 2 or parts[1] != "artifact-export":
        return None
    sid = parts[0]
    if not validate_session_id(sid):
        return None
    return sid


def post_artifact_export(
    workspace_root: Path,
    session_id: str,
    body: dict[str, Any],
) -> dict[str, Any]:
    from lenses.blueprints_wizard.artifact_export_markdown import render_artifact_bundle_markdown
    from lenses.blueprints_wizard.artifact_generation_normalize import ARTIFACT_SLICE_KEYS, normalize_artifact_generation

    if not validate_session_id(session_id):
        return {"ok": False, "error": "invalid_session_id"}
    doc = load_session(workspace_root, session_id)
    if doc is None:
        return {"ok": False, "error": "not_found"}
    raw_list = body.get("artifact_keys")
    if not isinstance(raw_list, list) or len(raw_list) == 0:
        return {"ok": False, "error": "invalid_artifact_keys"}
    keys: list[str] = []
    for x in raw_list:
        k = str(x).strip()
        if not k:
            continue
        if k not in ARTIFACT_SLICE_KEYS:
            return {"ok": False, "error": "invalid_artifact_key", "detail": k}
        keys.append(k)
    if not keys:
        return {"ok": False, "error": "invalid_artifact_keys"}
    wd = doc.payload.get("wizard_domain")
    if not isinstance(wd, dict):
        wd = {}
    ag = normalize_artifact_generation(wd.get("artifact_generation"))
    arts = ag.get("artifacts") or {}
    if not isinstance(arts, dict):
        arts = {}
    md = render_artifact_bundle_markdown(arts, keys)
    return {"ok": True, "markdown": md}


def parse_session_artifact_recheck_path(path: str) -> str | None:
    """If path is /api/blueprints/wizard/session/<id>/artifact-recheck, return session id."""
    prefix = "/api/blueprints/wizard/session/"
    if not path.startswith(prefix):
        return None
    rest = path[len(prefix) :].strip("/")
    parts = rest.split("/")
    if len(parts) != 2 or parts[1] != "artifact-recheck":
        return None
    sid = parts[0]
    if not validate_session_id(sid):
        return None
    return sid


def post_artifact_recheck(workspace_root: Path, session_id: str, body: dict[str, Any]) -> dict[str, Any]:
    from lenses.blueprints_wizard.artifact_recheck_service import run_artifact_recheck

    return run_artifact_recheck(workspace_root, session_id, body)


def parse_session_cursor_launch_pack_path(path: str, action: str) -> str | None:
    """
    Match ``/api/blueprints/wizard/session/<id>/cursor-launch-pack/<action>``.
    ``action`` is ``preview`` or ``export``.
    """
    prefix = "/api/blueprints/wizard/session/"
    if not path.startswith(prefix):
        return None
    rest = path[len(prefix) :].strip("/")
    parts = rest.split("/")
    if len(parts) != 3 or parts[1] != "cursor-launch-pack":
        return None
    if parts[2] != action:
        return None
    sid = parts[0]
    if not validate_session_id(sid):
        return None
    return sid


def post_cursor_launch_pack_preview(
    workspace_root: Path,
    session_id: str,
    body: dict[str, Any],
) -> dict[str, Any]:
    """Read-only compile for UI preview (no disk write)."""
    from lenses.blueprints_wizard.cursor_launch_pack import StrictApprovalError, preview_pack

    if not validate_session_id(session_id):
        return {"ok": False, "error": "invalid_session_id"}
    doc = load_session(workspace_root, session_id)
    if doc is None:
        return {"ok": False, "error": "not_found"}
    try:
        out = preview_pack(session_id, doc.payload, body)
        return out
    except StrictApprovalError as e:
        return {"ok": False, "error": "strict_approval_failed", "artifact_keys": e.keys}
    except ValueError as e:
        msg = str(e)
        if "invalid_artifact_keys" in msg:
            return {"ok": False, "error": "invalid_artifact_keys"}
        return {"ok": False, "error": "invalid_request", "detail": msg}


def _safe_write_pack_dir(workspace_root: Path, session_id: str, relative_path: str | None) -> Path:
    """Default under ``.lenses-local/blueprints-wizard/cursor-launch-packs/`` or validated subpath of workspace."""
    import re
    from datetime import datetime, timezone

    root = workspace_root.resolve()
    if relative_path and str(relative_path).strip():
        raw = str(relative_path).strip().replace("\\", "/")
        if raw.startswith("/") or ".." in Path(raw).parts:
            raise ValueError("invalid_relative_path")
        dest = (root / raw).resolve()
        try:
            dest.relative_to(root)
        except ValueError as exc:
            raise ValueError("invalid_relative_path") from exc
        return dest
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    safe_sid = re.sub(r"[^A-Za-z0-9._-]", "_", session_id)[:128]
    return root / ".lenses-local" / "blueprints-wizard" / "cursor-launch-packs" / safe_sid / ts


# Inline base64 zip only below this size; larger packs use staged file + GET download (see ``post_cursor_launch_pack_export``).
_MAX_LAUNCH_PACK_ZIP_INLINE_BYTES = 8 * 1024 * 1024


def parse_session_cursor_launch_pack_download_path(path: str) -> tuple[str, str] | None:
    """
    Match ``GET /api/blueprints/wizard/session/<id>/cursor-launch-pack/download/<token>``.
    Returns ``(session_id, token)``.
    """
    prefix = "/api/blueprints/wizard/session/"
    if not path.startswith(prefix):
        return None
    rest = path[len(prefix) :].strip("/")
    parts = rest.split("/")
    if len(parts) != 4:
        return None
    sid, seg, dl, token = parts
    if seg != "cursor-launch-pack" or dl != "download":
        return None
    if not validate_session_id(sid):
        return None
    from lenses.blueprints_wizard.launch_pack_staging import validate_download_token

    if not validate_download_token(token):
        return None
    return sid, token


def post_cursor_launch_pack_export(
    workspace_root: Path,
    session_id: str,
    body: dict[str, Any],
) -> dict[str, Any]:
    """Write pack to workspace or return zip as base64 or staged download token."""
    import base64

    from lenses.blueprints_wizard.cursor_launch_pack import (
        StrictApprovalError,
        build_launch_pack_zip_bytes,
        compile_cursor_launch_pack,
    )
    from lenses.blueprints_wizard.launch_pack_staging import write_staged_zip

    if not validate_session_id(session_id):
        return {"ok": False, "error": "invalid_session_id"}
    doc = load_session(workspace_root, session_id)
    if doc is None:
        return {"ok": False, "error": "not_found"}

    dest_kind = str(body.get("destination") or "workspace").strip().lower()
    rel_opt = body.get("relative_path")
    rel_str: str | None = str(rel_opt).strip() if rel_opt is not None and str(rel_opt).strip() else None

    try:
        pack, warnings = compile_cursor_launch_pack(session_id, doc.payload, body)
    except StrictApprovalError as e:
        return {"ok": False, "error": "strict_approval_failed", "artifact_keys": e.keys}
    except ValueError as e:
        msg = str(e)
        if "invalid_artifact_keys" in msg:
            return {"ok": False, "error": "invalid_artifact_keys"}
        return {"ok": False, "error": "invalid_request", "detail": msg}

    if dest_kind == "workspace":
        try:
            target = _safe_write_pack_dir(workspace_root, session_id, rel_str)
        except ValueError:
            return {"ok": False, "error": "invalid_relative_path"}
        target.mkdir(parents=True, exist_ok=True)
        root = workspace_root.resolve()
        for rel, text in pack.files:
            fp = target / rel
            fp = Path(fp)
            fp.parent.mkdir(parents=True, exist_ok=True)
            fp.write_text(text, encoding="utf-8")
        try:
            export_rel = str(target.relative_to(root))
        except ValueError:
            export_rel = str(target)
        return {
            "ok": True,
            "export_path_relative": export_rel,
            "file_count": len(pack.files),
            "warnings": warnings,
        }

    if dest_kind == "download":
        raw = build_launch_pack_zip_bytes(pack)
        name = f"cursor-launch-pack-{session_id[:16]}.zip"
        prefer_stream = body.get("stream") or body.get("prefer_stream")
        use_stream = prefer_stream is True or str(prefer_stream).strip().lower() in (
            "1",
            "true",
            "yes",
            "on",
        )
        if len(raw) > _MAX_LAUNCH_PACK_ZIP_INLINE_BYTES or use_stream:
            from urllib.parse import quote

            token = write_staged_zip(workspace_root, session_id, raw)
            enc_sid = quote(session_id, safe="")
            return {
                "ok": True,
                "download_mode": "stream",
                "download_token": token,
                "download_path": f"/api/blueprints/wizard/session/{enc_sid}/cursor-launch-pack/download/{token}",
                "byte_length": len(raw),
                "filename": name,
                "warnings": warnings,
            }
        return {
            "ok": True,
            "download_mode": "inline",
            "filename": name,
            "content_base64": base64.b64encode(raw).decode("ascii"),
            "byte_length": len(raw),
            "warnings": warnings,
        }

    return {"ok": False, "error": "invalid_destination"}


def post_wizard_telemetry_event(workspace_root: Path, body: dict[str, Any]) -> dict[str, Any]:
    """POST ``/api/blueprints/wizard/telemetry`` — client step/navigation events (opt-in)."""
    from lenses.blueprints_wizard.wizard_telemetry import ingest_client_event

    return ingest_client_event(workspace_root, body)
