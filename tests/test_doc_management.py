"""Tests for Doc Management session store and intake."""

from __future__ import annotations

import base64
import json
import zipfile
import io
from pathlib import Path

import pytest

from lenses.doc_management import intake as intake_mod
from lenses.doc_management import session_store as store
from lenses.doc_management.surface_catalog import catalog_payload


@pytest.fixture()
def workspace(tmp_path: Path) -> Path:
    (tmp_path / "forge-platform" / "docs-governance").mkdir(parents=True)
    (tmp_path / "forge-platform" / "docs-governance" / "persona_journey_map.yaml").write_text(
        "personas:\n  - persona_id: architect\n    main_question: test\n",
        encoding="utf-8",
    )
    (tmp_path / "forge-platform" / "docs-governance" / "surface_registry.yaml").write_text(
        "surfaces:\n  - surface_id: forgesdlc_blog\n    label: Blog\n    repo: forgesdlc\n    relative_path: blog\n",
        encoding="utf-8",
    )
    return tmp_path


def test_create_and_list_session(workspace: Path) -> None:
    sess = store.create_session(workspace, display_name="Test session")
    sid = sess["id"]
    loaded = store.load_session(workspace, sid)
    assert loaded is not None
    assert loaded["display_name"] == "Test session"
    rows = store.list_sessions(workspace)
    assert any(r["session_id"] == sid for r in rows)


def test_paste_intake(workspace: Path) -> None:
    sess = store.create_session(workspace)
    sid = sess["id"]
    intake_mod.apply_intake_to_session(
        workspace,
        sess,
        intake_source="paste",
        text="# Hello\n\nWorld",
    )
    loaded = store.load_session(workspace, sid)
    assert loaded is not None
    seeds = loaded["intake"]["seeds"]
    assert len(seeds) == 1
    seed_path = store.intake_dir(workspace, sid) / seeds[0]["name"]
    assert seed_path.is_file()
    assert "Hello" in seed_path.read_text(encoding="utf-8")


def test_zip_intake_two_md_files(workspace: Path) -> None:
    sess = store.create_session(workspace)
    sid = sess["id"]
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("a.md", "# A")
        zf.writestr("b.md", "# B")
    seeds, manual = intake_mod.normalize_zip_intake(workspace, sid, buf.getvalue())
    assert len(seeds) == 2
    assert manual == []
    intake_mod.apply_intake_to_session(
        workspace,
        sess,
        intake_source="zip",
        zip_bytes=buf.getvalue(),
    )
    loaded = store.load_session(workspace, sid)
    assert len(loaded["intake"]["seeds"]) == 2


def test_catalog_loads_surfaces(workspace: Path) -> None:
    payload = catalog_payload(workspace)
    assert payload["ok"] is True
    assert any(s["surface_id"] == "forgesdlc_blog" for s in payload["surfaces"])
