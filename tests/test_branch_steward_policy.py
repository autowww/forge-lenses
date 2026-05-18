from __future__ import annotations

from pathlib import Path

from lenses.branch_steward_policy import categorize_branch_name, resolve_branch_steward_policy


def test_categorize_branch_name_lane_prefixes() -> None:
    assert categorize_branch_name("main") == "main"
    assert categorize_branch_name("product/PS-1") == "product"
    assert categorize_branch_name("iter/F1-PS-1") == "iter"
    assert categorize_branch_name("spark/M2E1S1") == "spark"
    assert categorize_branch_name("spike/unknown") == "spike"
    assert categorize_branch_name("release/v1.2.3") == "release"
    assert categorize_branch_name("hotfix/critical") == "hotfix"
    assert categorize_branch_name("feature/x") == "feature"
    assert categorize_branch_name("fix/y") == "fix"


def test_resolve_branch_steward_policy_from_branching_yml(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / ".git").mkdir()
    (repo / "forge").mkdir()
    (repo / "forge" / "branching.yml").write_text(
        "\n".join(
            [
                "trunk: main",
                "model: forge_lanes",
                "team:",
                "  scale: team",
                "  topology: polyrepo",
                "  cicd_maturity: advanced",
                "promotion:",
                "  require_pr: true",
                "  required_approvals: 2",
                "  require_green_checks: true",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    p = resolve_branch_steward_policy(repo)
    assert p.model == "forge_lanes"
    assert p.trunk == "main"
    assert p.team_scale == "team"
    assert p.topology == "polyrepo"
    assert p.required_approvals == 2
    assert p.require_green_checks is True
