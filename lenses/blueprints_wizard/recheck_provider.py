"""Pluggable recheck / repair (future); experimental Blueprints Wizard."""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable

from lenses.blueprints_wizard.artifact_generation_recheck import ArtifactGenerationRecheckStub


@runtime_checkable
class RecheckProvider(Protocol):
    """Produces a normalized RecheckSummary dict from session payload (no I/O)."""

    def summarize(self, payload: dict[str, Any]) -> dict[str, Any]:
        ...


class NullRecheckProvider:
    """Default no-op: empty recheck summary."""

    def summarize(self, payload: dict[str, Any]) -> dict[str, Any]:
        from lenses.blueprints_wizard.wizard_domain_normalize import normalize_recheck_summary

        _ = payload
        return normalize_recheck_summary({})
