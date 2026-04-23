"""Communication artifacts: release notes, stakeholder summary, blocker digest."""

from __future__ import annotations

from typing import Any


def build_communication_artifacts(
    doc: dict[str, Any],
    cicd: dict[str, Any],
    quality: dict[str, Any] | None,
    devsecops: dict[str, Any] | None,
    packet: dict[str, Any],
) -> dict[str, Any]:
    focus = str(doc.get("focus_release_version") or "").strip()
    train = cicd.get("release_train") if isinstance(cicd.get("release_train"), dict) else {}
    ver = str(train.get("current_focus") or focus or "upcoming")

    crs = [c for c in doc.get("change_requests") or [] if isinstance(c, dict)]
    titles = [str(c.get("title") or c.get("id")) for c in crs]

    notes_lines = [
        f"# Release notes (draft) — {ver}",
        "",
        "## Highlights",
    ]
    for t in titles[:12]:
        notes_lines.append(f"- {t}")
    notes_lines.extend(["", "## Changes by initiative"])
    for ini in doc.get("initiatives") or []:
        if isinstance(ini, dict):
            notes_lines.append(f"- **{ini.get('name') or ini.get('id')}** — {ini.get('summary') or ''}".strip())

    stakeholder = [
        f"# Stakeholder summary — {ver}",
        "",
        "**Audience:** leadership and dependent product teams.",
        "",
        "## Outcome",
        f"We are targeting version **{ver}** on the train **{train.get('name') or 'current'}**.",
        "",
        "## Dependencies",
        "See cross-team dependency board in Lenses Plan → Today (Release manager).",
        "",
        "## Risks",
    ]
    for cr in crs[:5]:
        stakeholder.append(
            f"- **{cr.get('id')}** — risk `{cr.get('risk') or '?'}`: {cr.get('scope') or ''}".strip()
        )

    blocker_lines = ["# Blocker summary", ""]
    pkt_block = next((s for s in (packet.get("sections") or []) if s.get("title") == "What blocks it"), None)
    if isinstance(pkt_block, dict) and pkt_block.get("body_md"):
        blocker_lines.append(pkt_block["body_md"])
    else:
        blocker_lines.append("—")

    return {
        "release_notes_md": "\n".join(notes_lines),
        "stakeholder_summary_md": "\n".join(stakeholder),
        "blocker_summary_md": "\n".join(blocker_lines),
    }
