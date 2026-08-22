"""Adapter ports for CI/CD and traceability providers (GitHub, GitLab, Jenkins, …)."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class DeliverySignalsProvider(Protocol):
    """Merge remote or derived signals into a per-repository row.

    Implementations live under ``lenses/delivery_signals/providers/`` (stubs today; wire in serve layer
    when credentials and rate limits are defined). The domain payload is built in ``aggregate.py``.
    PR/MR normalization and merge-readiness widgets use ``lenses/repo_workflow/`` (Sprint 3, separate flag).
    """

    provider_id: str

    def augment_repo_row(
        self,
        *,
        workspace_root: Path,
        project: str,
        row: dict[str, Any],
    ) -> dict[str, Any]:
        """Return a copy of ``row`` with provider-specific keys set (workflows, trace_links, …)."""
        ...
