"""Orchestrate artifact generation and review actions; persist session."""

from __future__ import annotations

import os
import secrets
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from lenses.blueprints_wizard.artifact_generation_dependencies import (
    EXECUTION_SLICE_KEYS,
    assert_upstream_approved,
    build_lineage_upstream_entries,
    resolve_requested_artifact_keys,
    upstream_keys_for_generation,
)
from lenses.blueprints_wizard.artifact_generation_execution_readiness import (
    validate_scope_complete_for_execution,
)
from lenses.blueprints_wizard.artifact_generation_inputs import (
    canonical_inputs_fingerprint_payload,
    upstream_generation_id_map,
    validate_generation_prerequisites,
)
from lenses.blueprints_wizard.artifact_generation_llm import run_artifact_generation_llm
from lenses.blueprints_wizard.artifact_pack_sync import apply_pack_sync_to_document
from lenses.blueprints_wizard.artifact_generation_normalize import (
    ARTIFACT_SLICE_KEYS,
    implementation_tasklets_traceability_ok,
    merge_artifact_generation_bundle,
    normalize_artifact_generation,
    normalize_provenance,
)
from lenses.blueprints_wizard.mock_artifact_generation import MockArtifactGenerationAdapter
from lenses.blueprints_wizard.schemas import WizardSessionDocument
from lenses.blueprints_wizard.session_store import load_session, save_session_replace, validate_session_id
from lenses.blueprints_wizard.wizard_session_state import merge_wizard_domain


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def artifact_generation_mock_enabled() -> bool:
    raw = (os.environ.get("LENSES_ARTIFACT_GENERATION_MOCK") or "").strip().lower()
    return raw in ("1", "true", "yes", "on")


def _new_gen_id() -> str:
    return secrets.token_urlsafe(12)


def _stamp_records(
    artifacts: dict[str, Any],
    *,
    provider: str,
    model: str | None,
    fingerprint: str,
    parent_generation_id: str | None,
    lineage_upstream: list[dict[str, Any]],
) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for k, rec in artifacts.items():
        if not isinstance(rec, dict):
            continue
        prov = dict(rec.get("provenance") or {})
        prov["generation_id"] = _new_gen_id()
        prov["created_at"] = _utc_now_iso()
        prov["provider"] = provider[:64] if provider else ""
        prov["model"] = (model or "")[:200]
        prov["input_fingerprint"] = fingerprint[:128]
        if parent_generation_id:
            prov["parent_generation_id"] = parent_generation_id[:128]
        prov["lineage"] = {"upstream": list(lineage_upstream)}
        rec = dict(rec)
        rec["provenance"] = normalize_provenance(prov)
        out[k] = rec
    return out


def generate_artifacts(
    workspace_root: Path,
    session_id: str,
    body: dict[str, Any],
) -> dict[str, Any]:
    """
    Body: ``provider``, optional ``model``, ``refine`` (bool),
    optional ``artifact`` (single key), optional ``artifact_keys`` (list),
    optional ``artifact_bundle`` — ``planning`` | ``engineering`` | ``all``.
    Default bundle is planning-sized when none of these are set.
    """
    if not validate_session_id(session_id):
        return {"ok": False, "error": "invalid_session_id"}
    doc = load_session(workspace_root, session_id)
    if doc is None:
        return {"ok": False, "error": "not_found"}

    okp, err = validate_generation_prerequisites(doc)
    if not okp:
        return {"ok": False, "error": err or "prerequisites_not_met"}

    provider = str(body.get("provider", "")).strip().lower()
    model_raw = body.get("model")
    model_override: str | None
    if model_raw is None:
        model_override = None
    else:
        ms = str(model_raw).strip()
        model_override = ms if ms else None
    refine = bool(body.get("refine"))

    artifact_keys, resolve_err = resolve_requested_artifact_keys(body)
    if artifact_keys is None:
        if resolve_err == "invalid_artifact_keys":
            return {"ok": False, "error": "invalid_artifact_keys"}
        return {"ok": False, "error": "invalid_artifact_key", "detail": resolve_err or ""}

    exec_keys = frozenset(artifact_keys) & EXECUTION_SLICE_KEYS
    if exec_keys:
        ok_sc, err_sc, det_sc = validate_scope_complete_for_execution(doc)
        if not ok_sc:
            return {"ok": False, "error": err_sc or "scope_incomplete", "detail": det_sc or ""}

    pl = doc.payload
    wd_pl = pl.get("wizard_domain")
    if not isinstance(wd_pl, dict):
        wd_pl = {}
    ag_bundle = normalize_artifact_generation(wd_pl.get("artifact_generation"))
    existing_arts = ag_bundle.get("artifacts") or {}
    if not isinstance(existing_arts, dict):
        existing_arts = {}
    for k in artifact_keys:
        prev = existing_arts.get(k)
        if isinstance(prev, dict) and prev.get("locked") is True:
            return {"ok": False, "error": "artifact_locked", "detail": k}

    ok_up, err_up, det_up = assert_upstream_approved(artifact_keys, existing_arts)
    if not ok_up:
        return {"ok": False, "error": err_up or "upstream_not_approved", "detail": det_up or ""}

    up_keys = upstream_keys_for_generation(artifact_keys, existing_arts)
    up_gen_map = upstream_generation_id_map(existing_arts, up_keys)
    lineage_entries = build_lineage_upstream_entries(artifact_keys, existing_arts)
    fp = canonical_inputs_fingerprint_payload(
        doc.payload,
        upstream_generation_ids=up_gen_map,
        include_execution_scope=bool(exec_keys),
    )
    llm_extra: dict[str, Any] = {}

    if artifact_generation_mock_enabled():
        adapter = MockArtifactGenerationAdapter()
        inner = adapter.generate_bundle(
            workspace_root=workspace_root,
            session_payload=doc.payload,
            provider=provider or "mock",
            model_override=model_override,
            refine=refine,
            artifact_keys=artifact_keys,
        )
    else:
        if not provider:
            return {"ok": False, "error": "invalid_provider", "detail": "(empty)"}
        inner = run_artifact_generation_llm(
            workspace_root=workspace_root,
            session_payload=doc.payload,
            provider=provider,
            model_override=model_override,
            refine=refine,
            artifact_keys=artifact_keys,
        )

    if not inner.get("ok"):
        return inner

    artifacts = inner.get("artifacts")
    if not isinstance(artifacts, dict):
        return {"ok": False, "error": "artifact_generation_parse_error"}

    if "implementation_tasklets" in artifacts:
        it_rec = artifacts.get("implementation_tasklets")
        if isinstance(it_rec, dict):
            content = it_rec.get("content")
            if isinstance(content, dict) and not implementation_tasklets_traceability_ok(content):
                return {
                    "ok": False,
                    "error": "artifact_generation_parse_error",
                    "detail": "implementation_tasklets missing upstream_artifact refs",
                }

    parent_id = None
    if len(artifact_keys) == 1:
        k0 = next(iter(artifact_keys))
        p0 = existing_arts.get(k0)
        if isinstance(p0, dict):
            prov0 = p0.get("provenance")
            if isinstance(prov0, dict):
                parent_id = str(prov0.get("generation_id") or "").strip() or None

    stamped = _stamp_records(
        artifacts,
        provider=provider or "mock",
        model=inner.get("model") if isinstance(inner.get("model"), str) else model_override,
        fingerprint=fp,
        parent_generation_id=parent_id,
        lineage_upstream=lineage_entries,
    )

    replace_keys = artifact_keys

    merged_ag = merge_artifact_generation_bundle(
        ag_bundle,
        stamped,
        replace_keys=replace_keys,
    )

    new_doc = merge_wizard_domain(doc, {"artifact_generation": merged_ag})
    new_doc = apply_pack_sync_to_document(new_doc)

    ok_save, err_save = save_session_replace(workspace_root, session_id, new_doc.to_dict())
    if not ok_save:
        return {"ok": False, "error": err_save or "save_failed"}

    out: dict[str, Any] = {"ok": True, "session": new_doc.to_dict()}
    for k in ("model", "usage", "routing"):
        if k in inner:
            llm_extra[k] = inner[k]
    out.update(llm_extra)
    return out


def apply_artifact_review(
    workspace_root: Path,
    session_id: str,
    body: dict[str, Any],
) -> dict[str, Any]:
    """
    Body: ``action`` — approve | request_changes | lock | unlock | approve_bundle;
    ``artifact_key`` (single); or ``artifact_keys`` (list) for approve_bundle;
    optional ``feedback``.
    """
    if not validate_session_id(session_id):
        return {"ok": False, "error": "invalid_session_id"}
    doc = load_session(workspace_root, session_id)
    if doc is None:
        return {"ok": False, "error": "not_found"}

    action = str(body.get("action", "")).strip().lower()
    key = str(body.get("artifact_key", "")).strip()
    feedback = str(body.get("feedback", "")).strip()[:8_000]

    if action not in ("approve", "request_changes", "lock", "unlock", "approve_bundle"):
        return {"ok": False, "error": "invalid_review_action", "detail": action}

    wd = doc.payload.get("wizard_domain")
    if not isinstance(wd, dict):
        wd = {}
    ag = normalize_artifact_generation(wd.get("artifact_generation"))
    arts = dict(ag.get("artifacts") or {})

    if action == "approve_bundle":
        raw_list = body.get("artifact_keys")
        if not isinstance(raw_list, list) or len(raw_list) == 0:
            return {"ok": False, "error": "invalid_artifact_keys", "detail": ""}
        bundle_keys: list[str] = []
        for x in raw_list:
            k = str(x).strip()
            if not k:
                continue
            if k not in ARTIFACT_SLICE_KEYS:
                return {"ok": False, "error": "invalid_artifact_key", "detail": k}
            bundle_keys.append(k)
        if not bundle_keys:
            return {"ok": False, "error": "invalid_artifact_keys"}
        blocking: list[str] = []
        for k in bundle_keys:
            rec_b = arts.get(k)
            if not isinstance(rec_b, dict):
                blocking.append(f"missing:{k}")
                continue
            if rec_b.get("locked") is True:
                blocking.append(f"locked:{k}")
        if blocking:
            return {
                "ok": False,
                "error": "approve_bundle_blocked",
                "detail": ",".join(blocking),
            }
        for k in bundle_keys:
            rec_b = dict(arts[k])
            rec_b["review_status"] = "approved"
            rec_b["feedback"] = ""
            arts[k] = rec_b
        ag["artifacts"] = arts
        ag = normalize_artifact_generation(ag)
        new_doc = merge_wizard_domain(doc, {"artifact_generation": ag})
        new_doc = apply_pack_sync_to_document(new_doc)
        ok_save, err_save = save_session_replace(workspace_root, session_id, new_doc.to_dict())
        if not ok_save:
            return {"ok": False, "error": err_save or "save_failed"}
        return {"ok": True, "session": new_doc.to_dict()}

    if key not in ARTIFACT_SLICE_KEYS:
        return {"ok": False, "error": "invalid_artifact_key", "detail": key}

    rec = arts.get(key)
    if not isinstance(rec, dict):
        return {"ok": False, "error": "artifact_not_found", "detail": key}

    if rec.get("locked") is True and action not in ("lock", "unlock"):
        return {"ok": False, "error": "artifact_locked", "detail": key}

    rec = dict(rec)
    if action == "approve":
        rec["review_status"] = "approved"
        rec["feedback"] = ""
    elif action == "request_changes":
        rec["review_status"] = "changes_requested"
        rec["feedback"] = feedback
    elif action == "lock":
        rec["locked"] = True
        rec["review_status"] = "locked"
    elif action == "unlock":
        if rec.get("locked") is not True:
            return {"ok": False, "error": "artifact_not_locked", "detail": key}
        rec["locked"] = False
        rec["review_status"] = "pending"
        rec["feedback"] = ""

    arts[key] = rec
    ag["artifacts"] = arts
    ag = normalize_artifact_generation(ag)

    new_doc = merge_wizard_domain(doc, {"artifact_generation": ag})
    new_doc = apply_pack_sync_to_document(new_doc)
    ok_save, err_save = save_session_replace(workspace_root, session_id, new_doc.to_dict())
    if not ok_save:
        return {"ok": False, "error": err_save or "save_failed"}

    return {"ok": True, "session": new_doc.to_dict()}
