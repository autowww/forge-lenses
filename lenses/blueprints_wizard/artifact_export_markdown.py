"""Export selected wizard artifacts as Markdown (experimental)."""

from __future__ import annotations

from typing import Any


def _esc_cell(s: str) -> str:
    return str(s or "").replace("|", "\\|").replace("\n", " ")


def _artifact_record_to_markdown(key: str, rec: dict[str, Any]) -> str:
    lines: list[str] = [f"## {key}", ""]
    content = rec.get("content")
    if not isinstance(content, dict):
        lines.append("_(empty)_")
        lines.append("")
        return "\n".join(lines)

    if key == "foundation_brief_final":
        md = content.get("markdown")
        lines.append(str(md or ""))
        lines.append("")
        return "\n".join(lines)

    if key == "implementation_tasklets":
        tasklets = content.get("tasklets")
        lines.append("| id | title | upstream (artifact_key) |")
        lines.append("|---|---|---|")
        if isinstance(tasklets, list):
            for t in tasklets:
                if not isinstance(t, dict):
                    continue
                tid = _esc_cell(str(t.get("id", "")))
                title = _esc_cell(str(t.get("title", "")))
                ups = t.get("upstream_artifacts")
                u_s = ""
                if isinstance(ups, list):
                    parts = []
                    for u in ups:
                        if isinstance(u, dict):
                            parts.append(str(u.get("artifact_key", "")))
                    u_s = _esc_cell(", ".join(parts))
                lines.append(f"| {tid} | {title} | {u_s} |")
        lines.append("")
        return "\n".join(lines)

    if key == "sparks_plan":
        sparks = content.get("sparks")
        lines.append("| spark_id | story_ref | phase | status | intent |")
        lines.append("|---|---|---|---|---|")
        if isinstance(sparks, list):
            for s in sparks:
                if not isinstance(s, dict):
                    continue
                lines.append(
                    "| "
                    + " | ".join(
                        _esc_cell(str(s.get(x, "")))
                        for x in ("spark_id", "story_ref", "phase_prefix", "status", "intent")
                    )
                    + " |"
                )
        lines.append("")
        return "\n".join(lines)

    if key == "charge_plan":
        charges = content.get("charges")
        lines.append("| charge_id | sparks | owner | notes |")
        lines.append("|---|---|---|---|")
        if isinstance(charges, list):
            for c in charges:
                if not isinstance(c, dict):
                    continue
                sr = c.get("spark_refs")
                refs = ""
                if isinstance(sr, list):
                    refs = ", ".join(str(x) for x in sr if str(x).strip())
                lines.append(
                    f"| {_esc_cell(str(c.get('charge_id','')))} | {_esc_cell(refs)} | "
                    f"{_esc_cell(str(c.get('owner','')))} | {_esc_cell(str(c.get('notes','')))} |"
                )
        lines.append("")
        return "\n".join(lines)

    if key == "acceptance_criteria":
        crit = content.get("criteria")
        lines.append("| id | statement | tasklet | story |")
        lines.append("|---|---|---|---|")
        if isinstance(crit, list):
            for c in crit:
                if not isinstance(c, dict):
                    continue
                lines.append(
                    f"| {_esc_cell(str(c.get('id','')))} | {_esc_cell(str(c.get('statement','')))} | "
                    f"{_esc_cell(str(c.get('tasklet_id','')))} | {_esc_cell(str(c.get('story_ref','')))} |"
                )
        lines.append("")
        return "\n".join(lines)

    if key == "execution_dependency_sequence":
        steps = content.get("ordered_steps")
        lines.append("| seq | step_id | ref_type | ref_id |")
        lines.append("|---|---|---|---|")
        if isinstance(steps, list):
            for s in sorted(steps, key=lambda x: int(x.get("seq") or 0) if isinstance(x, dict) else 0):
                if not isinstance(s, dict):
                    continue
                lines.append(
                    f"| {s.get('seq','')} | {_esc_cell(str(s.get('step_id','')))} | "
                    f"{_esc_cell(str(s.get('ref_type','')))} | {_esc_cell(str(s.get('ref_id','')))} |"
                )
        lines.append("")
        return "\n".join(lines)

    if key == "qa_verification_checklist":
        items = content.get("items")
        lines.append("| id | check | evidence |")
        lines.append("|---|---|---|")
        if isinstance(items, list):
            for it in items:
                if not isinstance(it, dict):
                    continue
                lines.append(
                    f"| {_esc_cell(str(it.get('id','')))} | {_esc_cell(str(it.get('check','')))} | "
                    f"{_esc_cell(str(it.get('evidence','')))} |"
                )
        lines.append("")
        return "\n".join(lines)

    if key == "rollout_notes":
        for sec in content.get("sections") or []:
            if isinstance(sec, dict):
                lines.append(f"### {_esc_cell(str(sec.get('title','')))}")
                lines.append(str(sec.get("body") or ""))
                lines.append("")
        cn = content.get("canary_notes")
        if cn:
            lines.append("### Canary")
            lines.append(str(cn))
            lines.append("")
        return "\n".join(lines)

    # Generic: JSON-like fallback for remaining keys
    import json

    try:
        lines.append("```json")
        lines.append(json.dumps(content, ensure_ascii=False, indent=2)[:48_000])
        lines.append("```")
    except (TypeError, ValueError):
        lines.append(str(content)[:24_000])
    lines.append("")
    return "\n".join(lines)


def render_artifact_record_markdown(key: str, rec: dict[str, Any]) -> str:
    """Markdown for a single generated artifact record (e.g. launch pack ``nodes/*.md``)."""
    return _artifact_record_to_markdown(key, rec)


def render_artifact_bundle_markdown(artifacts: dict[str, Any], artifact_keys: list[str]) -> str:
    """Concatenate Markdown sections for requested keys (in order)."""
    parts: list[str] = ["# Blueprints Wizard — artifact export", ""]
    for key in artifact_keys:
        rec = artifacts.get(key)
        if not isinstance(rec, dict):
            parts.append(f"## {key}")
            parts.append("_(missing)_")
            parts.append("")
            continue
        parts.append(_artifact_record_to_markdown(key, rec))
    return "\n".join(parts).strip() + "\n"
