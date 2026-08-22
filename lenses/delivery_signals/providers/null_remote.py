"""No-op remote provider — placeholder for GitHub/GitLab/Jenkins implementations."""

from __future__ import annotations

from pathlib import Path
from typing import Any


class NullRemoteDeliveryProvider:
    """Returns rows unchanged; use when no remote integration is configured."""

    provider_id = "null_remote"

    def augment_repo_row(
        self,
        *,
        workspace_root: Path,
        project: str,
        row: dict[str, Any],
    ) -> dict[str, Any]:
        _ = (workspace_root, project)
        return dict(row)
