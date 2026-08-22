"""Product map board prefill from WBS / work model."""

from __future__ import annotations

from pathlib import Path

import pytest

from lenses.board_product_map import hydrate_board_from_product_map, resolve_project_plan_paths
from lenses.sticker_board import initial_state_for_session, registry_apply


@pytest.fixture
def mini_workspace(tmp_path: Path) -> Path:
    repo = tmp_path / "demo"
    req = repo / "docs" / "requirements"
    req.mkdir(parents=True)
    wbs_src = Path(__file__).parent / "fixtures" / "wbs-mini.md"
    (req / "WBS.md").write_text(wbs_src.read_text(encoding="utf-8"), encoding="utf-8")
    return tmp_path


def test_resolve_project_plan_paths(mini_workspace: Path) -> None:
    state = {
        "children": [{"name": "demo"}],
        "wbs": [
            {
                "rel_path": "demo/docs/requirements/WBS.md",
                "repo_hint": "demo",
                "kind": "wbs",
            }
        ],
        "roadmaps": [],
    }
    paths = resolve_project_plan_paths(mini_workspace, state, "demo")
    assert paths["repo"] == "demo"
    assert paths["wbs_p"].endswith("WBS.md")


def test_hydrate_board_from_product_map(mini_workspace: Path) -> None:
    state = initial_state_for_session("product_map_workshop", "local")
    wbs_p = "demo/docs/requirements/WBS.md"
    out, meta = hydrate_board_from_product_map(
        mini_workspace,
        state,
        repo="demo",
        wbs_p=wbs_p,
        session_template="product_map_workshop",
    )
    assert meta["prefill_ok"] is True
    assert meta["stickers_added"] >= 2
    assert out.get("prefill_applied") is True
    kinds = {s.get("source_kind") for s in out.get("stickers") or []}
    assert "story" in kinds or "epic" in kinds


def test_registry_create_product_map_prefill(mini_workspace: Path) -> None:
    scan = {
        "children": [{"name": "demo"}],
        "wbs": [
            {
                "rel_path": "demo/docs/requirements/WBS.md",
                "repo_hint": "demo",
            }
        ],
        "roadmaps": [],
    }
    ok, err, extra = registry_apply(
        mini_workspace,
        None,
        {"demo"},
        "create",
        {
            "project": "demo",
            "label": "Product map",
            "storage": "local",
            "session_template": "product_map_workshop",
            "prefill": True,
            "_workspace_scan_state": scan,
        },
    )
    assert ok, err
    pre = (extra or {}).get("prefill") or {}
    assert pre.get("prefill_ok") is True or (extra or {}).get("prefill_message") == "ok"
