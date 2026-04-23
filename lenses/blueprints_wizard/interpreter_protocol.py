"""Service boundary for Blueprints Wizard interpretation (experimental)."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Protocol


class InterpretationRunner(Protocol):
    """Produces a normalized interpretation dict or an error-shaped result."""

    def run(
        self,
        *,
        workspace_root: Path,
        session_payload: dict[str, Any],
        provider: str,
        model_override: str | None,
        refine: bool,
    ) -> dict[str, Any]:
        ...
