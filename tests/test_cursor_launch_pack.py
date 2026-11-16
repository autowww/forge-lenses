"""Cursor Launch Pack — manifest and scope-limited export."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from lenses.blueprints_wizard.api import post_cursor_launch_pack_export, post_cursor_launch_pack_preview
from lenses.blueprints_wizard.artifact_generation_service import generate_artifacts
from lenses.blueprints_wizard.cursor_launch_pack import (
    LAUNCH_PACK_MANIFEST_VERSION,
    CompiledLaunchPack,
    build_launch_pack_zip_bytes,
    compile_cursor_launch_pack,
)
from lenses.blueprints_wizard.launch_pack_staging import consume_staged_zip, staged_zip_path, write_staged_zip
from lenses.blueprints_wizard.schemas import WizardSessionDocument, normalize_wizard_payload
from lenses.blueprints_wizard.session_store import create_session, load_session, save_session_replace
from lenses.blueprints_wizard.wizard_domain_normalize import normalize_run_plan


def _minimal_session(tmp_path: Path) -> str:
    sid = create_session(tmp_path)
    doc = load_session(tmp_path, sid)
    assert doc is not None
    pl = dict(doc.payload)
    wd = dict(pl.get("wizard_domain") or {})
    wd["foundation_brief"] = {"markdown": "x", "field_statuses": {}}
    wd["run_plan"] = normalize_run_plan(
        {"title": "P", "steps": [{"id": "1", "title": "S", "detail": ""}]}
    )
    wd["scope_spec"] = dict(wd.get("scope_spec") or {})
    wd["scope_spec"]["scope_boundary"] = "full_plan"
    wd["scope_spec"]["closure_options"] = ["exact_only"]
    pl["wizard_domain"] = wd
    pl["foundation_brief"] = "x"
    doc2 = WizardSessionDocument.from_dict({**doc.to_dict(), "payload": normalize_wizard_payload(pl)})
    assert doc2 is not None
    save_session_replace(tmp_path, sid, doc2.to_dict())
    return sid


def test_manifest_generation_contains_schema_and_session(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("LENSES_ARTIFACT_GENERATION_MOCK", "1")
    sid = _minimal_session(tmp_path)
    g = generate_artifacts(tmp_path, sid, {"provider": "openai", "artifact": "roadmap"})
    assert g.get("ok") is True

    doc = load_session(tmp_path, sid)
    assert doc is not None
    pack, _warnings = compile_cursor_launch_pack(
        sid,
        doc.payload,
        {"artifact_keys": ["roadmap"], "closure_options": ["exact_only"]},
    )
    assert pack.manifest["schema_version"] == LAUNCH_PACK_MANIFEST_VERSION
    assert pack.manifest["session_id"] == sid
    assert pack.manifest["expanded_artifact_keys"] == ["roadmap"]
    assert "manifest.json" in [p for p, _ in pack.files]


def test_preview_api_matches_compile(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LENSES_ARTIFACT_GENERATION_MOCK", "1")
    sid = _minimal_session(tmp_path)
    generate_artifacts(tmp_path, sid, {"provider": "openai", "artifact": "roadmap"})

    out = post_cursor_launch_pack_preview(
        tmp_path,
        sid,
        {"artifact_keys": ["roadmap"], "closure_options": ["exact_only"]},
    )
    assert out.get("ok") is True
    man = out.get("manifest")
    assert isinstance(man, dict)
    assert man.get("session_id") == sid
    assert man.get("expanded_artifact_keys") == ["roadmap"]
    files = out.get("files")
    assert isinstance(files, list)
    paths = [f.get("path") for f in files if isinstance(f, dict)]
    assert "nodes/roadmap.md" in paths


def test_scope_upstream_expansion_includes_upstream_artifact(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("LENSES_ARTIFACT_GENERATION_MOCK", "1")
    sid = _minimal_session(tmp_path)
    generate_artifacts(tmp_path, sid, {"provider": "openai", "artifact": "prd"})

    doc = load_session(tmp_path, sid)
    assert doc is not None
    exact, _ = compile_cursor_launch_pack(
        sid,
        doc.payload,
        {"artifact_keys": ["prd"], "closure_options": ["exact_only"]},
    )
    assert exact.manifest["expanded_artifact_keys"] == ["prd"]

    up, _ = compile_cursor_launch_pack(
        sid,
        doc.payload,
        {"artifact_keys": ["prd"], "closure_options": ["include_required_upstream"]},
    )
    keys = up.manifest["expanded_artifact_keys"]
    assert "prd" in keys
    assert "foundation_brief_final" in keys
    assert "roadmap" in keys


def test_workspace_export_writes_files(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LENSES_ARTIFACT_GENERATION_MOCK", "1")
    sid = _minimal_session(tmp_path)
    generate_artifacts(tmp_path, sid, {"provider": "openai", "artifact": "roadmap"})

    out = post_cursor_launch_pack_export(
        tmp_path,
        sid,
        {
            "artifact_keys": ["roadmap"],
            "closure_options": ["exact_only"],
            "destination": "workspace",
        },
    )
    assert out.get("ok") is True
    rel = str(out.get("export_path_relative") or "")
    assert rel
    root = tmp_path.resolve()
    written = root / rel / "manifest.json"
    assert written.is_file()
    data = json.loads(written.read_text(encoding="utf-8"))
    assert data.get("expanded_artifact_keys") == ["roadmap"]


def test_strict_approval_fails_when_slices_pending(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("LENSES_ARTIFACT_GENERATION_MOCK", "1")
    sid = _minimal_session(tmp_path)
    generate_artifacts(tmp_path, sid, {"provider": "openai", "artifact": "roadmap"})

    out = post_cursor_launch_pack_preview(
        tmp_path,
        sid,
        {"artifact_keys": ["roadmap"], "closure_options": ["exact_only"], "strict_approval": True},
    )
    assert out.get("ok") is False
    assert out.get("error") == "strict_approval_failed"
    keys = out.get("artifact_keys")
    assert isinstance(keys, list)
    assert "roadmap" in keys


def test_strict_approval_succeeds_when_approved(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("LENSES_ARTIFACT_GENERATION_MOCK", "1")
    sid = _minimal_session(tmp_path)
    generate_artifacts(tmp_path, sid, {"provider": "openai", "artifact": "roadmap"})
    doc = load_session(tmp_path, sid)
    assert doc is not None
    pl = dict(doc.payload)
    wd = dict(pl.get("wizard_domain") or {})
    ag = dict(wd.get("artifact_generation") or {})
    arts = dict(ag.get("artifacts") or {})
    r = dict(arts.get("roadmap") or {})
    r["review_status"] = "approved"
    arts["roadmap"] = r
    ag["artifacts"] = arts
    wd["artifact_generation"] = ag
    pl["wizard_domain"] = wd
    doc2 = WizardSessionDocument.from_dict({**doc.to_dict(), "payload": normalize_wizard_payload(pl)})
    assert doc2 is not None
    save_session_replace(tmp_path, sid, doc2.to_dict())

    out = post_cursor_launch_pack_preview(
        tmp_path,
        sid,
        {"artifact_keys": ["roadmap"], "closure_options": ["exact_only"], "strict_approval": True},
    )
    assert out.get("ok") is True


def test_download_prefers_stream_when_requested(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("LENSES_ARTIFACT_GENERATION_MOCK", "1")
    sid = _minimal_session(tmp_path)
    generate_artifacts(tmp_path, sid, {"provider": "openai", "artifact": "roadmap"})

    out = post_cursor_launch_pack_export(
        tmp_path,
        sid,
        {
            "artifact_keys": ["roadmap"],
            "closure_options": ["exact_only"],
            "destination": "download",
            "stream": True,
        },
    )
    assert out.get("ok") is True
    assert out.get("download_mode") == "stream"
    assert out.get("download_path")
    assert not out.get("content_base64")


def test_staging_write_and_resolve_roundtrip(tmp_path: Path) -> None:
    raw = build_launch_pack_zip_bytes(
        CompiledLaunchPack(manifest={"x": 1}, files=[("a.txt", "hi")]),
    )
    tok = write_staged_zip(tmp_path, "sess1", raw)
    p = staged_zip_path(tmp_path, "sess1", tok)
    assert p is not None
    assert p.read_bytes() == raw
    consume_staged_zip(p)
    assert not p.exists()
