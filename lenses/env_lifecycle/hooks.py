"""Lenses Studio consumer hooks for environment lifecycle lmeta flows."""

from __future__ import annotations

from typing import Any, Callable


def make_env_lifecycle_hooks(
    *,
    persist_environment: Callable[[dict[str, Any]], dict[str, Any]] | None = None,
    persist_deploy: Callable[[dict[str, Any]], dict[str, Any]] | None = None,
    persist_health: Callable[[dict[str, Any]], dict[str, Any]] | None = None,
    checkpoint_pipeline: Callable[[dict[str, Any]], dict[str, Any]] | None = None,
) -> dict[str, Callable[[dict[str, Any]], dict[str, Any]]]:
    hooks: dict[str, Callable[[dict[str, Any]], dict[str, Any]]] = {}

    def _wrap(name: str, fn: Callable[[dict[str, Any]], dict[str, Any]] | None):
        if fn is None:
            return lambda payload: {"ok": True, "skipped": True, "hook": name}
        return fn

    hooks["persist_environment"] = _wrap("persist_environment", persist_environment)
    hooks["persist_deploy"] = _wrap("persist_deploy", persist_deploy)
    hooks["persist_health"] = _wrap("persist_health", persist_health)
    hooks["checkpoint_pipeline"] = _wrap("checkpoint_pipeline", checkpoint_pipeline)
    return hooks
