"""HTTP handlers for Doc Management API (invoked from ``serve.py``)."""

from __future__ import annotations

import base64
import json
import urllib.parse
from pathlib import Path
from typing import Any, Callable

from lenses.doc_management.feature_flag import doc_management_enabled
from lenses.doc_management import intake as intake_mod
from lenses.doc_management import manifest as manifest_mod
from lenses.doc_management import promote as promote_mod
from lenses.doc_management import runner as runner_mod
from lenses.doc_management import session_store as store
from lenses.doc_management.session_projection import session_public_view
from lenses.doc_management.surface_catalog import catalog_payload

SendJson = Callable[[int, dict[str, Any]], None]


def _disabled(send_json: SendJson) -> None:
    send_json(404, {"ok": False, "error": "feature_disabled"})


def get_catalog(workspace_root: Path, *, send_json: SendJson) -> None:
    if not doc_management_enabled():
        _disabled(send_json)
        return
    send_json(200, catalog_payload(workspace_root))


def get_sessions(workspace_root: Path, *, send_json: SendJson) -> None:
    if not doc_management_enabled():
        _disabled(send_json)
        return
    send_json(200, {"ok": True, "sessions": store.list_sessions(workspace_root)})


def get_session(workspace_root: Path, session_id: str, *, send_json: SendJson) -> None:
    if not doc_management_enabled():
        _disabled(send_json)
        return
    view = session_public_view(workspace_root, session_id)
    if view is None:
        send_json(404, {"ok": False, "error": "session_not_found"})
        return
    send_json(200, {"ok": True, "session": view})


def post_doc_management(workspace_root: Path, body: dict[str, Any], *, send_json: SendJson) -> None:
    if not doc_management_enabled():
        _disabled(send_json)
        return
    op = str(body.get("op") or "").strip()
    if op == "create_session":
        wizard = body.get("wizard") if isinstance(body.get("wizard"), dict) else None
        name = str(body.get("display_name") or "Doc management session").strip()
        sess = store.create_session(workspace_root, display_name=name, wizard=wizard)
        send_json(200, {"ok": True, "session": session_public_view(workspace_root, sess["id"])})
        return
    if op == "session_get":
        sid = str(body.get("session_id") or "").strip()
        get_session(workspace_root, sid, send_json=send_json)
        return
    if op == "session_cancel":
        sid = str(body.get("session_id") or "").strip()
        sess = store.cancel_session(workspace_root, sid)
        if not sess:
            send_json(404, {"ok": False, "error": "session_not_found"})
            return
        send_json(200, {"ok": True, "session": session_public_view(workspace_root, sid)})
        return
    if op == "session_intake":
        sid = str(body.get("session_id") or "").strip()
        sess = store.load_session(workspace_root, sid)
        if not sess:
            send_json(404, {"ok": False, "error": "session_not_found"})
            return
        try:
            src = str(body.get("intake_source") or "").strip()
            zip_b64 = body.get("zip_base64")
            zip_bytes = base64.b64decode(zip_b64) if zip_b64 else None
            sess = intake_mod.apply_intake_to_session(
                workspace_root,
                sess,
                intake_source=src,
                text=str(body.get("text") or ""),
                zip_bytes=zip_bytes,
                url=str(body.get("url") or "").strip() or None,
                blog_slug=str(body.get("blog_slug") or "").strip() or None,
                display_name=str(body.get("display_name") or "").strip() or None,
            )
        except ValueError as exc:
            send_json(400, {"ok": False, "error": str(exc)})
            return
        send_json(200, {"ok": True, "session": session_public_view(workspace_root, sid)})
        return
    if op == "session_wizard":
        sid = str(body.get("session_id") or "").strip()
        sess = store.load_session(workspace_root, sid)
        if not sess:
            send_json(404, {"ok": False, "error": "session_not_found"})
            return
        wizard = sess.setdefault("wizard", {})
        if not isinstance(wizard, dict):
            wizard = {}
            sess["wizard"] = wizard
        patch = body.get("wizard") if isinstance(body.get("wizard"), dict) else body
        for key in ("step_index", "persona", "target_surfaces", "use_llm", "intake_source", "source_url", "blog_slug"):
            if key in patch and patch[key] is not None:
                wizard[key] = patch[key]
        if body.get("display_name"):
            sess["display_name"] = str(body.get("display_name"))
        store.save_session(workspace_root, sess)
        send_json(200, {"ok": True, "session": session_public_view(workspace_root, sid)})
        return
    if op == "session_run":
        sid = str(body.get("session_id") or "").strip()
        try:
            sess = runner_mod.run_hydration_pipeline(workspace_root, sid)
        except ValueError as exc:
            send_json(400, {"ok": False, "error": str(exc)})
            return
        except RuntimeError as exc:
            send_json(500, {"ok": False, "error": str(exc)})
            return
        send_json(200, {"ok": True, "session": session_public_view(workspace_root, sess["id"])})
        return
    if op == "session_decisions":
        sid = str(body.get("session_id") or "").strip()
        reviewer = str(body.get("reviewer") or "studio_operator")
        decisions = body.get("decisions") if isinstance(body.get("decisions"), list) else []
        try:
            manifest = manifest_mod.write_manifest(workspace_root, sid, reviewer=reviewer, decisions=decisions)
        except ValueError as exc:
            send_json(400, {"ok": False, "error": str(exc)})
            return
        send_json(200, {"ok": True, "manifest": manifest, "session": session_public_view(workspace_root, sid)})
        return
    if op == "session_promote":
        sid = str(body.get("session_id") or "").strip()
        dry_run = body.get("dry_run", True)
        if isinstance(dry_run, str):
            dry_run = dry_run.lower() not in ("0", "false", "no")
        surfaces = body.get("surfaces") if isinstance(body.get("surfaces"), list) else None
        try:
            result = promote_mod.promote_session(workspace_root, sid, dry_run=bool(dry_run), surfaces=surfaces)
        except ValueError as exc:
            send_json(400, {"ok": False, "error": str(exc)})
            return
        code = 200 if result.get("ok") else 500
        send_json(code, {"ok": result.get("ok"), "result": result, "session": session_public_view(workspace_root, sid)})
        return
    if op == "session_rollback":
        sid = str(body.get("session_id") or "").strip()
        try:
            result = promote_mod.rollback_session(workspace_root, sid)
        except ValueError as exc:
            send_json(400, {"ok": False, "error": str(exc)})
            return
        code = 200 if result.get("ok") else 500
        send_json(code, {"ok": result.get("ok"), "result": result, "session": session_public_view(workspace_root, sid)})
        return
    send_json(400, {"ok": False, "error": "unknown_op"})


def put_session_wizard(
    workspace_root: Path,
    session_id: str,
    body: dict[str, Any],
    *,
    send_json: SendJson,
) -> None:
    if not doc_management_enabled():
        _disabled(send_json)
        return
    post_doc_management(
        workspace_root,
        {"op": "session_wizard", "session_id": session_id, **body},
        send_json=send_json,
    )
