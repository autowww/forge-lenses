"""Per-target export renderers for Sprint B5 handoff packages (no hardcoded agent behavior)."""

from __future__ import annotations

import json
from typing import Any

from lenses.bridge.handoff_bridge_registry import load_handoff_bridge_registry


def _substitute(template: str, ctx: dict[str, str]) -> str:
    out = template
    for k, v in ctx.items():
        out = out.replace("{{" + k + "}}", v)
    return out


def build_export_context(
    *,
    title: str,
    objective: str,
    work_unit_lines: list[str],
    acceptance: list[str],
    scope_boundaries: list[str],
    files_of_interest: list[str],
    recipes: list[str],
    tasklets: list[str],
    gate_expectations: list[str],
    output_contract_text: str,
    artifact_lines: list[str],
    launch_pack_version: str,
    target_key: str,
) -> dict[str, str]:
    reg = load_handoff_bridge_registry()
    tmeta = (reg.get("targets") or {}).get(target_key) or {}
    label = str(tmeta.get("label") or target_key)
    rb = "\n".join(f"- {x}" for x in recipes) or "—"
    if tasklets:
        rb += "\n**Tasklets:**\n" + "\n".join(f"- {x}" for x in tasklets)
    return {
        "title": title,
        "objective": objective,
        "work_units": "\n".join(f"- {x}" for x in work_unit_lines) or "—",
        "acceptance_criteria": "\n".join(f"- {x}" for x in acceptance) or "—",
        "scope_boundaries": "\n".join(f"- {x}" for x in scope_boundaries) or "—",
        "files_of_interest": "\n".join(f"- `{x}`" for x in files_of_interest) or "—",
        "recipes_block": rb,
        "tasklets_block": "\n".join(f"- {x}" for x in tasklets) or "—",
        "gate_expectations": "\n".join(f"- {x}" for x in gate_expectations) or "—",
        "output_contract": output_contract_text or "—",
        "artifacts_block": "\n".join(f"- {x}" for x in artifact_lines) or "—",
        "launch_pack_version": launch_pack_version or "unknown",
        "target_label": label,
    }


def render_markdown_pack(ctx: dict[str, str], target_key: str) -> str:
    reg = load_handoff_bridge_registry()
    tpls = ((reg.get("templates") or {}).get("markdown_pack") or {})
    raw = str(tpls.get(target_key) or tpls.get("cursor") or "# {{title}}\n{{objective}}\n")
    return _substitute(raw, ctx)


def render_task_file(ctx: dict[str, str], target_key: str) -> str:
    reg = load_handoff_bridge_registry()
    tpls = ((reg.get("templates") or {}).get("task_file") or {})
    raw = str(tpls.get(target_key) or tpls.get("cursor") or "")
    return _substitute(raw, ctx)


def render_summary_card(ctx: dict[str, str], target_key: str) -> str:
    reg = load_handoff_bridge_registry()
    tpls = ((reg.get("templates") or {}).get("summary_card") or {})
    raw = str(tpls.get(target_key) or tpls.get("cursor") or "")
    return _substitute(raw, ctx)


def render_json_manifest_dict(
    *,
    title: str,
    objective: str,
    work_unit_ids: list[str],
    acceptance_criteria: list[str],
    scope_boundaries: list[str],
    files_of_interest: list[str],
    recipes: list[str],
    tasklets: list[str],
    gate_expectations: list[str],
    output_contract: dict[str, Any] | str,
    launch_pack_version: str,
    target_key: str,
) -> dict[str, Any]:
    oc: Any = output_contract
    if isinstance(output_contract, str) and output_contract.strip():
        try:
            oc = json.loads(output_contract)
        except json.JSONDecodeError:
            oc = {"text": output_contract}
    elif not isinstance(output_contract, dict):
        oc = {}
    return {
        "handoff_version": "1",
        "target": target_key,
        "title": title,
        "objective": objective,
        "work_unit_ids": work_unit_ids,
        "acceptance_criteria": acceptance_criteria,
        "scope_boundaries": scope_boundaries,
        "files_of_interest": files_of_interest,
        "recipes": recipes,
        "tasklets": tasklets,
        "gate_expectations": gate_expectations,
        "output_contract": oc,
        "launch_pack_version": launch_pack_version,
    }


def render_all_exports(
    *,
    target_key: str,
    title: str,
    objective: str,
    work_unit_ids: list[str],
    acceptance_criteria: list[str],
    scope_boundaries: list[str],
    files_of_interest: list[str],
    recipes: list[str],
    tasklets: list[str],
    gate_expectations: list[str],
    output_contract: dict[str, Any] | str,
    artifact_lines: list[str],
    launch_pack_version: str,
) -> dict[str, Any]:
    oc_text = (
        json.dumps(output_contract, indent=2)
        if isinstance(output_contract, dict)
        else str(output_contract or "")
    )
    ctx = build_export_context(
        title=title,
        objective=objective,
        work_unit_lines=work_unit_ids,
        acceptance=acceptance_criteria,
        scope_boundaries=scope_boundaries,
        files_of_interest=files_of_interest,
        recipes=recipes,
        tasklets=tasklets,
        gate_expectations=gate_expectations,
        output_contract_text=oc_text,
        artifact_lines=artifact_lines,
        launch_pack_version=launch_pack_version,
        target_key=target_key,
    )
    manifest = render_json_manifest_dict(
        title=title,
        objective=objective,
        work_unit_ids=work_unit_ids,
        acceptance_criteria=acceptance_criteria,
        scope_boundaries=scope_boundaries,
        files_of_interest=files_of_interest,
        recipes=recipes,
        tasklets=tasklets,
        gate_expectations=gate_expectations,
        output_contract=output_contract,
        launch_pack_version=launch_pack_version,
        target_key=target_key,
    )
    return {
        "markdown_pack": render_markdown_pack(ctx, target_key),
        "json_manifest": json.dumps(manifest, indent=2, sort_keys=True),
        "task_file": render_task_file(ctx, target_key),
        "summary_card": render_summary_card(ctx, target_key),
    }
