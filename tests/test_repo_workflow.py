"""Repo workflow normalization and aggregate (Sprint 3)."""

from __future__ import annotations

from pathlib import Path

import pytest

from lenses.repo_workflow.adapters.azure_repos import normalize_azure_repos_snapshot
from lenses.repo_workflow.adapters.github import normalize_github_snapshot
from lenses.repo_workflow.adapters.gitlab import normalize_gitlab_snapshot
from lenses.repo_workflow.aggregate import (
    build_repo_workflow_overview_payload,
    get_repo_workflow_row_for_project,
)
from lenses.repo_workflow.feature_flag import experimental_repo_workflow_enabled
from lenses.repo_workflow.normalized import compute_health


def test_github_normalize_pull_request_fields() -> None:
    raw = {
        "repository": {"full_name": "o/r", "default_branch": "main", "html_url": "https://github.com/o/r"},
        "pull_requests": [
            {
                "id": 1,
                "number": 10,
                "title": "x",
                "state": "open",
                "head": {"ref": "f", "sha": "abc"},
                "base": {"ref": "main", "sha": "def"},
                "mergeable": "clean",
                "pending_review_count": 1,
                "stale_days": 8,
                "html_url": "https://github.com/o/r/pull/10",
            }
        ],
    }
    out = normalize_github_snapshot(raw)
    assert out["pull_requests"][0]["head_ref"] == "f"
    assert out["pull_requests"][0]["review_debt_count"] == 1
    h = compute_health(out)
    assert h["open_prs_count"] == 1
    assert h["stale_open_prs_count"] == 1


def test_gitlab_merge_request_maps_to_pull_requests() -> None:
    raw = {
        "project": {"path_with_namespace": "g/p", "web_url": "https://gitlab.com/g/p", "default_branch": "main"},
        "merge_requests": [
            {
                "iid": 3,
                "title": "MR",
                "state": "opened",
                "source_branch": "a",
                "target_branch": "main",
                "web_url": "https://gitlab.com/g/p/-/merge_requests/3",
            }
        ],
    }
    out = normalize_gitlab_snapshot(raw)
    assert out["pull_requests"][0]["number"] == 3
    assert out["repository"]["vcs_host_kind"] == "gitlab"


def test_azure_repos_pull_request() -> None:
    raw = {
        "project": {"name": "MyProj"},
        "repository": {"name": "r", "webUrl": "https://dev.azure.com/o/p/_git/r"},
        "pullRequests": [
            {
                "pullRequestId": 55,
                "title": "fix",
                "status": "active",
                "sourceRefName": "refs/heads/fix",
                "targetRefName": "refs/heads/main",
            }
        ],
    }
    out = normalize_azure_repos_snapshot(raw)
    assert out["pull_requests"][0]["number"] == 55
    assert out["pull_requests"][0]["head_ref"] == "fix"


def test_overview_disabled(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("LENSES_EXPERIMENTAL_REPO_WORKFLOW", "0")
    assert experimental_repo_workflow_enabled() is False
    scan = {"children": [{"name": "a", "is_git": True, "git": {}}], "resolved_at": "t"}
    out = build_repo_workflow_overview_payload(workspace_root=tmp_path, scan_state=scan, force_flag=False)
    assert out["feature_enabled"] is False


def test_overview_demo_seed(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.delenv("LENSES_EXPERIMENTAL_REPO_WORKFLOW", raising=False)
    monkeypatch.setenv("LENSES_REPO_WORKFLOW_SEED_DEMO", "1")
    scan = {
        "children": [{"name": "forgesdlc", "is_git": True, "git": {"branch": "main", "head_short": "abc"}}],
        "resolved_at": "t",
    }
    out = build_repo_workflow_overview_payload(workspace_root=tmp_path, scan_state=scan, force_flag=True)
    assert out["feature_enabled"] is True
    assert out["provider_kind"] == "local_fixture"
    repos = out["repos"]
    assert len(repos) == 1
    assert repos[0]["project"] == "forgesdlc"
    assert repos[0]["health"]["open_prs_count"] >= 2
    assert repos[0]["health"]["blocked_merge_count"] >= 1


def test_get_row_for_project_demo(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("LENSES_REPO_WORKFLOW_SEED_DEMO", "1")
    row = get_repo_workflow_row_for_project(tmp_path, "forgesdlc")
    assert row is not None
    assert row["provider"] == "github"
    links = row["work_item_links"]
    assert any(str(x.get("story_id")) == "S-1842" for x in links if isinstance(x, dict))
