"""Run environment lifecycle lmeta flows in-process (consumer hooks required)."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Callable

from forge_lcdl.flow.executor import FlowExecutor
from forge_lcdl.flow.resolve import resolve


def _flows_root() -> Path:
    code = Path(__file__).resolve().parents[2]
    sibling = code.parent / "forge-cdp-manager" / "flows"
    if sibling.is_dir():
        return sibling
    return Path.home() / "Code" / "forge-cdp-manager" / "flows"


def _loader(unit_id: str) -> dict[str, Any]:
    import json

    path = _flows_root() / "units" / f"{unit_id}.lmeta"
    return json.loads(path.read_text(encoding="utf-8"))


def run_env_lifecycle_flow(
    flow_doc: dict[str, Any],
    *,
    inputs: dict[str, Any],
    run_lcdl: Callable[..., dict[str, Any]],
    consumer_hooks: dict[str, Callable[[dict[str, Any]], dict[str, Any]]] | None = None,
) -> dict[str, Any]:
    canonical = resolve(flow_doc, _loader)
    executor = FlowExecutor(run_lcdl=run_lcdl, consumer_hooks=consumer_hooks or {})
    return executor.run(canonical, inputs=inputs)
