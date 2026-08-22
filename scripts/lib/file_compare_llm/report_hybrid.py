"""
Human-first Markdown for hybrid compare (Pass 2 + Pass 3 + evidence appendix).
"""

from __future__ import annotations

import json
from typing import Any


def _esc(s: str) -> str:
    return s.replace("|", "\\|").replace("\n", " ")


def render_comparison_report(
    *,
    merged: dict[str, Any],
    name_a: str,
    name_b: str,
    technical_extra: dict[str, Any] | None = None,
) -> str:
    """
    merged must contain keys: evidence, file_profiles, pass2 (optional), pass3 (optional).
    If pass3 missing (deterministic-only), render evidence-led stub.
    """
    lines: list[str] = []
    lines.append("# Comparison report")
    lines.append("")

    p3 = merged.get("pass3") if isinstance(merged.get("pass3"), dict) else None
    p2 = merged.get("pass2") if isinstance(merged.get("pass2"), dict) else None
    evidence = merged.get("evidence") or {}

    lines.append("## Executive summary")
    lines.append("")
    err = merged.get("pipeline_error")
    if isinstance(err, str) and err.strip():
        lines.append(f"- **Incomplete analysis:** {_esc(err.strip())}")
        lines.append("")
    if p3 and isinstance(p3.get("executive_summary_bullets"), list):
        for b in p3["executive_summary_bullets"]:
            lines.append(f"- {_esc(str(b))}")
    else:
        lines.append(
            "- *LLM passes were not run (`--deterministic-only`) or the model did not return a summary.* "
            "See the appendix for deterministic evidence."
        )
    lines.append("")

    lines.append("## Scorecard")
    lines.append("")
    lines.append(f"| Dimension | File A ({_esc(name_a)}) | File B ({_esc(name_b)}) | Winner | Why it matters |")
    lines.append("| --- | ---: | ---: | --- | --- |")
    if p3 and isinstance(p3.get("scorecard"), list):
        for row in p3["scorecard"]:
            if not isinstance(row, dict):
                continue
            lines.append(
                "| "
                + " | ".join(
                    [
                        _esc(str(row.get("dimension_id", ""))),
                        _esc(str(row.get("file_a", ""))),
                        _esc(str(row.get("file_b", ""))),
                        _esc(str(row.get("winner", ""))),
                        _esc(str(row.get("why_it_matters", ""))),
                    ]
                )
                + " |"
            )
    else:
        lines.append("| — | — | — | — | *No model scorecard.* |")
    lines.append("")

    lines.append("## What is common")
    lines.append("")
    if p3 and isinstance(p3.get("what_is_common"), list) and p3["what_is_common"]:
        for x in p3["what_is_common"]:
            lines.append(f"- {_esc(str(x))}")
    elif p2 and isinstance(p2.get("common_themes"), list):
        for x in p2["common_themes"]:
            lines.append(f"- {_esc(str(x))}")
    else:
        lines.append("—")
    lines.append("")

    lines.append("## Material differences")
    lines.append("")
    subs = (
        "scope",
        "depth",
        "quality",
        "completeness",
        "consistency",
        "clearness",
        "domain_fidelity",
        "structural_integrity",
    )
    md: dict[str, Any] = {}
    if isinstance(p2, dict):
        m = p2.get("material_differences")
        if isinstance(m, dict):
            md = m
    if isinstance(md, dict):
        titles = {
            "scope": "Scope",
            "depth": "Depth",
            "quality": "Quality",
            "completeness": "Completeness",
            "consistency": "Consistency",
            "clearness": "Clearness",
            "domain_fidelity": "Domain fidelity",
            "structural_integrity": "Structural integrity",
        }
        for k in subs:
            body = md.get(k) if isinstance(md.get(k), str) else ""
            lines.append(f"### {titles.get(k, k.capitalize())}")
            lines.append("")
            lines.append(body.strip() if body.strip() else "*Not highlighted by the model for this run.*")
            lines.append("")
    else:
        lines.append("*No material difference block from Pass 2.*")
        lines.append("")

    lines.append("## Entity-by-entity material deltas")
    lines.append("")
    lines.append("| Entity | Common ground | Difference | Why it matters | Preferred version |")
    lines.append("| --- | --- | --- | --- | --- |")
    rows = (p3 or {}).get("entity_deltas") if isinstance(p3, dict) else None
    if isinstance(rows, list) and rows:
        for row in rows:
            if not isinstance(row, dict):
                continue
            lines.append(
                "| "
                + " | ".join(
                    _esc(str(row.get(k, "")))
                    for k in ("entity", "common_ground", "difference", "why_it_matters", "preferred_version")
                )
                + " |"
            )
    else:
        lines.append("| — | — | — | — | — |")
    lines.append("")

    lines.append("## Bottom line for a human reviewer")
    lines.append("")
    if p3 and isinstance(p3.get("human_bottom_line"), str) and p3["human_bottom_line"].strip():
        lines.append(p3["human_bottom_line"].strip())
    else:
        lines.append("*No bottom-line narrative from the model.*")
    lines.append("")

    lines.append("## Appendix: deterministic evidence")
    lines.append("")
    lines.append("The following is **machine-generated evidence** (not the model’s prose). It supports triage and debugging.")
    lines.append("")
    lines.append("```json")
    lines.append(json.dumps(evidence, indent=2, ensure_ascii=False))
    lines.append("```")
    lines.append("")

    fps = merged.get("file_profiles") if isinstance(merged.get("file_profiles"), dict) else {}
    wa = fps.get("a") if isinstance(fps.get("a"), dict) else {}
    wb = fps.get("b") if isinstance(fps.get("b"), dict) else {}
    nw_a = wa.get("normalization_warnings") if isinstance(wa.get("normalization_warnings"), list) else []
    nw_b = wb.get("normalization_warnings") if isinstance(wb.get("normalization_warnings"), list) else []
    if nw_a or nw_b:
        lines.append("### Normalization warnings (per file)")
        lines.append("")
        if nw_a:
            lines.append(f"- **File A:** " + "; ".join(_esc(str(x)) for x in nw_a))
        if nw_b:
            lines.append(f"- **File B:** " + "; ".join(_esc(str(x)) for x in nw_b))
        lines.append("")

    if p3 and isinstance(p3.get("appendix_notes"), str) and p3["appendix_notes"].strip():
        lines.append("### How the model used this evidence")
        lines.append("")
        lines.append(p3["appendix_notes"].strip())
        lines.append("")

    if technical_extra:
        lines.append("## Appendix: technical extras (`--technical-markdown`)")
        lines.append("")
        lines.append("```json")
        lines.append(json.dumps(technical_extra, indent=2, ensure_ascii=False))
        lines.append("```")
        lines.append("")

    return "\n".join(lines)
