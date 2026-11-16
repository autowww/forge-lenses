"""Docs contract resolution (DOCS-1)."""

from __future__ import annotations

from pathlib import Path

from lenses.docs_health.contract import (
    contract_status_payload,
    load_project_docs_contract,
    resolve_project_docs_contract,
)


def test_inventory_empty_repo(tmp_path: Path) -> None:
    (tmp_path / ".git").mkdir()
    c = resolve_project_docs_contract(tmp_path, project_slug="empty")
    c["require_adr"] = False
    c["require_release_note"] = False
    c["require_architecture_diagram"] = False
    c["readme_required_sections"] = []
    from lenses.docs_health.inventory import build_inventory_snapshot

    snap = build_inventory_snapshot(tmp_path, project_slug="empty", contract=c)
    assert snap["document_count"] == 0
    assert snap["documents"] == []


def test_convention_defaults_when_no_file(tmp_path: Path) -> None:
    r = resolve_project_docs_contract(tmp_path, project_slug="myrepo")
    assert r["_meta"]["source"] == "convention"
    assert r["_meta"]["contract_path"] is None
    assert r["scope"]["repository"] == "myrepo"
    assert isinstance(r["required_doc_types"], list) and len(r["required_doc_types"]) >= 3


def test_forge_contract_file_merged(tmp_path: Path) -> None:
    (tmp_path / "forge").mkdir(parents=True)
    (tmp_path / "forge" / "docs-contract.yaml").write_text(
        "version: 2\nownership:\n  team: Platform\nreadme_required_sections:\n  - Overview\n",
        encoding="utf-8",
    )
    r = resolve_project_docs_contract(tmp_path, project_slug="x")
    assert r["_meta"]["source"] == "repo_file"
    assert r["_meta"]["contract_path"] == "forge/docs-contract.yaml"
    assert r["version"] == 2
    assert r["ownership"]["team"] == "Platform"
    st = contract_status_payload(tmp_path, r)
    assert st["mode"] == "configured"
    assert st["uses_convention_defaults"] is False


def test_legacy_lenses_contract_still_readable(tmp_path: Path) -> None:
    (tmp_path / "lenses-docs-contract.yaml").write_text(
        "require_adr: false\nrequire_release_note: false\n",
        encoding="utf-8",
    )
    raw = load_project_docs_contract(tmp_path)
    assert raw.get("require_adr") is False
    r = resolve_project_docs_contract(tmp_path, project_slug="z")
    assert r["_meta"].get("legacy_path_used")


def test_fixture_repo_inventory_and_links() -> None:
    root = Path(__file__).resolve().parent / "fixtures" / "docs_health_sample_repo"
    assert root.is_dir()
    c = resolve_project_docs_contract(root, project_slug="sample")
    from lenses.docs_health.inventory import build_inventory_snapshot

    snap = build_inventory_snapshot(root, project_slug="sample", contract=c)
    paths = {d["path"] for d in snap["documents"]}
    assert "README.md" in paths
    readme = next(d for d in snap["documents"] if d["path"] == "README.md")
    assert any("overview" in (h.get("text") or "").lower() for h in readme.get("headings", []))
    assert readme.get("doc_type") == "readme"
    assert "docs/guide/nested.md" in paths
    assert any(e.get("target_raw") == "../../README.md" and e.get("resolved") is True for e in snap["link_graph"])
    assert any(e.get("from_path") == "README.md" and e.get("resolved") is False for e in snap["link_graph"])
