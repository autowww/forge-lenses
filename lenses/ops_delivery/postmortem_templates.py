"""Built-in postmortem templates; merged with fixture ``postmortem_templates``."""

from __future__ import annotations

from typing import Any

_BUILTIN: list[dict[str, Any]] = [
    {
        "id": "pm-tpl-blameless-default",
        "title": "Blameless postmortem (default)",
        "linked_work_item_hint": "Link to tracking story / epic in WBS",
        "sections_md": "\n".join(
            [
                "## Summary",
                "- What happened? One paragraph.",
                "## Customer impact",
                "- Duration, scope, SLIs affected",
                "## Timeline",
                "- Detection → mitigation → recovery",
                "## Root causes",
                "- Technical and process",
                "## What went well",
                "",
                "## Action items",
                "| Owner | Action | Due |",
                "|-------|--------|-----|",
            ]
        ),
    },
    {
        "id": "pm-tpl-change-correlated",
        "title": "Change-correlated incident",
        "linked_work_item_hint": "Tie to release version and promotion id from CI/CD",
        "sections_md": "\n".join(
            [
                "## Suspected change",
                "- Release / artifact / flag exposure",
                "## Evidence",
                "- Deploy time vs incident start; dashboards",
                "## Rollback / mitigation",
                "- What was executed",
                "## Follow-up",
                "- Tests, guardrails, feature flags",
            ]
        ),
    },
]


def merged_templates(doc: dict[str, Any]) -> list[dict[str, Any]]:
    custom = [t for t in doc.get("postmortem_templates") or [] if isinstance(t, dict)]
    seen = {str(t.get("id")) for t in custom}
    out = list(custom)
    for b in _BUILTIN:
        bid = str(b.get("id") or "")
        if bid and bid not in seen:
            out.append(dict(b))
    return out
