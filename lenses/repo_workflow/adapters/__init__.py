"""Provider adapters (normalization only in Sprint 3)."""

from lenses.repo_workflow.adapters.azure_repos import normalize_azure_repos_snapshot
from lenses.repo_workflow.adapters.github import normalize_github_snapshot
from lenses.repo_workflow.adapters.gitlab import normalize_gitlab_snapshot

__all__ = [
    "normalize_azure_repos_snapshot",
    "normalize_github_snapshot",
    "normalize_gitlab_snapshot",
]
