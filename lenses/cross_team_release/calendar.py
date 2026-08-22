"""Release calendar: milestones, freezes, CAB, implementation windows."""

from __future__ import annotations

from typing import Any


def build_release_calendar(doc: dict[str, Any], cicd: dict[str, Any]) -> dict[str, Any]:
    events: list[dict[str, Any]] = []

    for m in doc.get("milestones") or []:
        if not isinstance(m, dict):
            continue
        events.append(
            {
                "type": "milestone",
                "start": str(m.get("at") or m.get("start") or ""),
                "end": str(m.get("end") or ""),
                "title": str(m.get("title") or m.get("id") or "Milestone"),
                "status": str(m.get("status") or ""),
                "ref_id": str(m.get("id") or ""),
                "release_version": str(m.get("release_version") or ""),
            }
        )

    for fw in cicd.get("freeze_windows") or []:
        if not isinstance(fw, dict):
            continue
        events.append(
            {
                "type": "freeze_window",
                "start": str(fw.get("start") or ""),
                "end": str(fw.get("end") or ""),
                "title": str(fw.get("name") or fw.get("id") or "Freeze"),
                "active": bool(fw.get("active")),
                "ref_id": str(fw.get("id") or ""),
                "blocks_promotion_to": list(fw.get("blocks_promotion_to") or [])
                if isinstance(fw.get("blocks_promotion_to"), list)
                else [],
            }
        )

    for cr in doc.get("change_requests") or []:
        if not isinstance(cr, dict):
            continue
        win = cr.get("implementation_window")
        if isinstance(win, dict) and (win.get("start") or win.get("end")):
            events.append(
                {
                    "type": "implementation_window",
                    "start": str(win.get("start") or ""),
                    "end": str(win.get("end") or ""),
                    "title": f"Implement: {cr.get('title') or cr.get('id')}",
                    "ref_id": str(cr.get("id") or ""),
                    "timezone": str(win.get("timezone") or "UTC"),
                }
            )

    for cab in doc.get("cab_sessions") or []:
        if not isinstance(cab, dict):
            continue
        events.append(
            {
                "type": "cab",
                "start": str(cab.get("scheduled_at") or ""),
                "end": "",
                "title": f"CAB — {cab.get('id') or 'session'}",
                "ref_id": str(cab.get("id") or ""),
                "change_request_ids": list(cab.get("change_request_ids") or [])
                if isinstance(cab.get("change_request_ids"), list)
                else [],
            }
        )

    events.sort(key=lambda x: (x.get("start") or "9999", x.get("type") or ""))
    return {"events": events}
