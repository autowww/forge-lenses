"""Adapter contracts: GitHub, GitLab, Azure Repos → normalized workflow rows.

Implementations are **pure normalizers** (dict in → dict out). Live HTTP clients can wrap vendor SDK
responses into the same *input* shapes documented on each adapter module.
"""

from __future__ import annotations

from typing import Any, Literal, Protocol, runtime_checkable

ProviderKind = Literal["github", "gitlab", "azure_repos"]


@runtime_checkable
class RepoWorkflowAdapter(Protocol):
    """Contract for vendor-specific normalization."""

    provider: ProviderKind

    def normalize_repo_snapshot(self, raw: dict[str, Any]) -> dict[str, Any]:
        """Map a provider-shaped repository snapshot to **workflow v1** (see ``normalized.WORKFLOW_V1_KEYS``)."""
