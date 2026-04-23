"""Go / no-go meeting packet from fixture + live CI/CD, quality, security hints."""

from __future__ import annotations

from typing import Any


def _md_escape(s: str) -> str:
    return (s or "").replace("\r\n", "\n").strip()


def build_go_no_go_packet(
    doc: dict[str, Any],
    cicd: dict[str, Any],
    quality: dict[str, Any] | None,
    devsecops: dict[str, Any] | None,
) -> dict[str, Any]:
    focus = str(doc.get("focus_release_version") or "").strip()
    train = cicd.get("release_train") if isinstance(cicd.get("release_train"), dict) else {}
    focus_display = str(train.get("current_focus") or focus or "—")

    sections: list[dict[str, str]] = []

    lines_ship: list[str] = []
    lines_ship.append(f"- **Release train focus:** {focus_display}")
    if train.get("name"):
        lines_ship.append(f"- **Train:** {train.get('name')}")
    cands = train.get("candidates") or []
    if isinstance(cands, list):
        for c in cands[:8]:
            if isinstance(c, dict):
                lines_ship.append(
                    f"- Candidate **{c.get('version')}** — status `{c.get('status')}`"
                    + (f" — [{c.get('changelog_url')}]" if c.get("changelog_url") else "")
                )
    sections.append({"title": "What ships", "body_md": "\n".join(lines_ship) or "—"})

    blockers: list[str] = []
    for b in cicd.get("blocked_promotions") or []:
        if not isinstance(b, dict):
            continue
        blockers.append(
            f"- Promotion `{b.get('promotion_id')}` — **{b.get('reason')}** — {b.get('detail') or ''}".strip()
        )
    rq = (quality or {}).get("release_quality") if isinstance(quality, dict) else None
    if isinstance(rq, dict) and rq.get("ready") is False:
        blockers.append(f"- **Quality train:** {rq.get('summary') or 'Not ready'}")
    sg = (devsecops or {}).get("security_release_gate") if isinstance(devsecops, dict) else None
    if isinstance(sg, dict) and sg.get("passed") is False:
        blockers.append(f"- **Security / compliance:** {sg.get('summary') or 'Gate failed'}")
    sections.append(
        {
            "title": "What blocks it",
            "body_md": "\n".join(blockers) if blockers else "— No blockers recorded in merged live data —",
        }
    )

    dep_lines: list[str] = []
    for e in doc.get("dependency_edges") or []:
        if not isinstance(e, dict):
            continue
        fk = str(e.get("from_kind") or "node")
        tk = str(e.get("to_kind") or "node")
        fi = str(e.get("from_ref") or e.get("from_id") or "")
        ti = str(e.get("to_ref") or e.get("to_id") or "")
        note = f" — {e['note']}" if e.get("note") else ""
        dep_lines.append(
            f"- `{fk}:{fi}` → `{tk}:{ti}` ({e.get('relation') or 'rel'}){note}"
        )
    sections.append(
        {
            "title": "Cross-team dependencies",
            "body_md": "\n".join(dep_lines) if dep_lines else "—",
        }
    )

    appr_lines: list[str] = []
    for cr in doc.get("change_requests") or []:
        if not isinstance(cr, dict):
            continue
        cid = str(cr.get("id") or "")
        for a in cr.get("approvers") or []:
            if not isinstance(a, dict):
                continue
            appr_lines.append(
                f"- **{cid}** — {a.get('role') or 'approver'}: `{a.get('status') or '?'}`"
                + (f" ({a.get('login')})" if a.get("login") else "")
                + (f" @ {a.get('at')}" if a.get("at") else "")
            )
    for cab in doc.get("cab_sessions") or []:
        if not isinstance(cab, dict):
            continue
        for d in cab.get("decisions") or []:
            if not isinstance(d, dict):
                continue
            appr_lines.append(
                f"- **CAB** `{cab.get('id')}` — CHG `{d.get('change_request_id')}` → **{d.get('decision')}**"
                + (f" — {d.get('notes')}" if d.get("notes") else "")
            )
    sections.append(
        {
            "title": "Who approved it (CAB-lite)",
            "body_md": "\n".join(appr_lines) if appr_lines else "—",
        }
    )

    rb_lines: list[str] = []
    for r in cicd.get("rollback_targets") or []:
        if not isinstance(r, dict):
            continue
        ver = str(r.get("rollback_target_version") or r.get("target_version") or r.get("version") or "")
        rb_lines.append(
            f"- **{r.get('environment_id') or r.get('id')}** → rollback target version `{ver}`"
            + (f" (approval: {r.get('approval_status')})" if r.get("approval_status") else "")
        )
    for cr in doc.get("change_requests") or []:
        if not isinstance(cr, dict):
            continue
        note = str(cr.get("rollback_notes") or "").strip()
        if note:
            rb_lines.append(f"- **{cr.get('id')}:** {note}")
    sections.append(
        {
            "title": "How to roll back",
            "body_md": "\n".join(rb_lines) if rb_lines else "—",
        }
    )

    md_parts = [f"# Go / no-go packet\n\n_Generated from live workspace data + `cross-team-release` fixture._\n"]
    for s in sections:
        md_parts.append(f"## {_md_escape(s['title'])}\n\n{_md_escape(s['body_md'])}\n")

    return {"sections": sections, "markdown": "\n".join(md_parts)}
