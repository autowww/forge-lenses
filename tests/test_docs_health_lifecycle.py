"""Finding lifecycle between Docs Health scans."""

from __future__ import annotations

from pathlib import Path

from lenses.docs_health import store


def test_lifecycle_reopened_after_returning_finding(tmp_path: Path) -> None:
    ws = tmp_path / "ws"
    ws.mkdir()
    slug = "demo"
    store.ensure_store_dir(ws, slug)
    # First scan: two findings
    a = store.update_finding_lifecycle(ws, slug, prior_ids=set(), current_ids={"f1", "f2"})
    assert a["new_since_prior_scan"]
    # Second: one resolved
    b = store.update_finding_lifecycle(ws, slug, prior_ids={"f1", "f2"}, current_ids={"f2"})
    assert "f1" in b["resolved_from_prior_scan"]
    # Third: f1 returns
    c = store.update_finding_lifecycle(ws, slug, prior_ids={"f2"}, current_ids={"f1", "f2"})
    assert "f1" in c["reopened_findings"]


def test_upsert_work_items_merge(tmp_path: Path) -> None:
    ws = tmp_path / "ws"
    ws.mkdir()
    slug = "demo"
    store.ensure_store_dir(ws, slug)
    n1 = store.upsert_docs_debt_work_items(
        ws,
        slug,
        [
            {
                "id": "docs-debt-x",
                "title": "A",
                "status": "open",
                "kind": "ktlo",
                "finding_id": "x",
                "run_id": "r1",
            }
        ],
    )
    assert n1 == 1
    n2 = store.upsert_docs_debt_work_items(
        ws,
        slug,
        [
            {
                "id": "docs-debt-x",
                "title": "A updated",
                "status": "open",
                "kind": "ktlo",
                "finding_id": "x",
                "run_id": "r2",
            }
        ],
    )
    assert n2 == 0
    rows = store.load_work_items(ws, slug)
    assert len(rows) == 1
    assert rows[0].get("title") == "A updated"
