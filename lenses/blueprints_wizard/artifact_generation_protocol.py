"""Protocol for artifact bundle generation (LLM or mock)."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class ArtifactGenerationPort(Protocol):
    def generate_bundle(
        self,
        *,
        workspace_root: Path,
        session_payload: dict[str, Any],
        provider: str,
        model_override: str | None,
        refine: bool,
        artifact_keys: frozenset[str],
    ) -> dict[str, Any]:
        """Return ``{ ok: True, artifacts: { key: record dict } }`` or ``{ ok: False, error, detail? }``."""
        ...
